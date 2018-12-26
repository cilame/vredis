import redis

from threading import Thread, RLock
import json
import time
import queue
import traceback
import logging
import random

from . import defaults
from . import common
from .utils import (
    hook_console, 
    _stdout, 
    _stderr,
    check_connect_sender, 
    Valve, 
    TaskEnv,
)
from .pipeline import (
    send_to_pipeline,
    send_to_pipeline_data,
    from_pipeline_execute,
)
from .order import (
    cmdline_command,
    script_command,
)

from .error import NotInDefaultType

class Worker(common.Initer):

    def __init__(self, 
            rds             = redis.StrictRedis(),
            workerid        = None
        ):

        def wait_connect_pub_worker(self):
            rname = '{}:{}'.format(defaults.VREDIS_PUBLISH_WORKER, self.workerid)
            self._pub = self.rds.pubsub()
            self._pub.subscribe(rname)
            while not self.rds.pubsub_numsub(rname)[0][1]:
                time.sleep(.15)
            self._pubn = int(self.rds.pubsub_numsub(rname)[0][1]) # 一个源于redis自身的问题，这里不一定是1，所以需要进行传递处理。

        self.rds            = rds
        self.rds.ping()

        self.lock           = RLock()
        self.pub            = self.rds.pubsub()
        self.pub.subscribe(defaults.VREDIS_PUBLISH_WORKER)

        self.pull_task      = queue.Queue()
        self.cmdline_task   = queue.Queue() # 暂未用到
        self.workerid       = self.rds.hincrby(defaults.VREDIS_WORKER, defaults.VREDIS_WORKER_ID)\
                                if workerid is None else workerid

        self.tasklist       = set()
        hook_console()
        wait_connect_pub_worker(self) # 开启任务前需要等待自连接广播打开，用于任意形式工作端断开能被发送任务端检测到

        self._thread_num    = 0 # 用以计算当前使用的 pull_task 线程数量，在挂钩停止任务时判断是否 “不使用线程池”

    @classmethod
    def from_settings(cls, **kw):
        rds = cls.redis_from_settings(**kw)
        d = dict(
            workerid = None
        )
        # 配置类参数
        for i in kw:
            if i in d:
                d[i] = kw[i]
            if hasattr(defaults,i):
                setattr(defaults,i,kw[i])
        return cls(rds=rds,**d)

    # 拆分函数
    @staticmethod
    def disassemble_func(func,start=None,err=None,stop=None):
        def _disassemble(*a,**kw):
            return func, a, kw, start, err, stop
        return _disassemble

    def connect_work_queue(self,_queue,taskid,workerid,order):
        def _task_func(task_func):
            def pack_task(*a,**kw):
                # 给任务注入“开始回调”、“错误回调”和“停止回调”的函数,放进线程执行队列
                _start = self.disassemble_func(send_to_pipeline)(self,taskid,workerid,order,'start',plus=self._pubn)
                _error = self.disassemble_func(send_to_pipeline)(self,taskid,workerid,order,'error')
                _stop  = self.disassemble_func(send_to_pipeline)(self,taskid,workerid,order,'stop')
                _task  = self.disassemble_func(task_func,start=_start,err=_error,stop=_stop)(*a,**kw)
                _queue.put(_task)
            return pack_task
        return _task_func


    def process_order(self):
        print('open worker id:',self.workerid)
        for i in self.pub.listen(): # 这里的设计无法抵御网络中断
            # 过滤订阅信息
            if i['type'] == 'subscribe': continue
            order       = json.loads(i['data'])
            workerid    = self.workerid
            taskid      = order['taskid']
            order       = order['order']
            pull_looper = self.connect_work_queue(self.pull_task,   taskid,workerid,order)
            cmdl_looper = self.connect_work_queue(self.cmdline_task,taskid,workerid,order) # 暂未用到

            if   order['command'] == 'cmdline': cmdl_looper(cmdline_command)(self,taskid,workerid,order)
            elif order['command'] == 'script':  pull_looper(script_command) (self,taskid,workerid,order)

    def _thread(self,_queue):
        while True:
            func,args,kwargs,start,err,stop = _queue.get()
            with common.Initer.lock: self._thread_num += 1
            def task(func,args,kwargs,start,err,stop):
                # 为了使 stack 寻找时候定位当前的环境从而找到 taskid 来分割不同任务的日志环境
                # 需要确保这里的 locals() 空间内拥有该参数名并且其余的环境没有该参数名字
                # 具体使用详细见 utils 内的 hook 类的函数实现（听不懂就算了，总之就是很魔法）
                __very_unique_function_name__ = None
                taskid      = start[1][1]
                workerid    = start[1][2]
                order       = start[1][3]
                rds         = self.rds
                valve       = Valve(taskid)
                rdm         = self.rds.hincrby(defaults.VREDIS_WORKER, taskid)
                # 阀门过滤，有配置用配置，没有配置就会用 defaults 里面的默认参数
                # 使用时就当作一般的 defaults 来进行配置即可。
                try:
                    valve.update(order['settings'])
                    if start is not None:
                        start_callback,a,kw,_,_,_ = start
                        start_callback(*a,**kw)
                    func(*args,**kwargs)
                except:
                    if err is not None:
                        err_callback,a,kw,_,_,_ = err
                        err_callback(*a,**kw,msg=traceback.format_exc())
                    if valve.VREDIS_CMDLINE is None: valve.delete(taskid)
                    TaskEnv.delete(taskid)
                finally:
                    self.rds.hdel(defaults.VREDIS_WORKER, taskid)
                    if stop is not None:
                        stop_callback,a,kw,_,_,_ = stop
                        if self._thread_num < defaults.VREDIS_WORKER_THREAD_TASK_NUM:
                            stop_callback(*a,**kw,plus=(valve,TaskEnv))
                        else:
                            print('Warning! More than {} tasks are currently being performed, workerid:{}.' \
                                            .format(self._thread_num-1,workerid))
                            Thread(target=stop_callback,args=a,kwargs={**kw,'plus':(valve,TaskEnv)}).start()
                    _stdout._clear_cache(taskid)
                    _stderr._clear_cache(taskid)
            task(func,args,kwargs,start,err,stop)
            with common.Initer.lock: self._thread_num -= 1

    def _thread_run(self):
        while True:
            for etask in list(TaskEnv.__taskenv__):
                # 为了安全的实现 worker 的缓冲任务能够在crash后分派给别的任务，这里替换成新的处理方式
                ret,rdata = from_pipeline_execute(self, etask)
                if rdata:
                    taskid      = rdata['taskid']
                    func_name   = rdata['function'] # 抽取传递过来的函数名字
                    args        = rdata['args']
                    kwargs      = rdata['kwargs']
                    plus        = rdata['plus']
                    TaskEnv.incr(taskid)

                    func_str    = '{}(*{},**{})'.format(func_name,args,kwargs)
                    taskenv     = TaskEnv.get_env_locals(taskid)

                    # 魔法参数，以及为了兼顾魔法的发生而需要的 get_task_locals 函数
                    # 看着没用实际有用（用于挂钩标准输出流）
                    __very_unique_function_name__ = None
                    taskid,workerid,order,rds,valve,rdm = TaskEnv.get_task_locals(taskid)
                    table = plus.get('table',valve.VREDIS_DATA_DEFAULT_TABLE)

                    if check_connect_sender(rds, taskid, order['sender_pubn']):
                        try:
                            data = eval(func_str, None, taskenv)
                            send_to_pipeline_data(self,taskid,data,ret,table,valve)
                        except:
                            # 这里的设计无法抵御网络中断
                            send_to_pipeline(self,taskid,workerid,order,'error',traceback.format_exc())
                        finally:
                            TaskEnv.decr(taskid)
                    else:
                        TaskEnv.decr(taskid)
                        continue # 这是为了考虑 redis 的存储量所做的队列清空处理
            time.sleep(defaults.VREDIS_WORKER_IDLE_TIME)

    # 用于将广播的任务信号拖拽下来进行环境配置的线程群
    def process_pull_task(self):
        for i in range(defaults.VREDIS_WORKER_THREAD_TASK_NUM):
            Thread(target=self._thread,args=(self.pull_task,)).start()

    # 直接执行任务的线程群
    def process_run_task(self):
        for i in range(defaults.VREDIS_WORKER_THREAD_RUN_NUM):
            Thread(target=self._thread_run).start()

    # 这里将作为命令行传输执行的管道
    def process_run_cmdline(self):
        for i in range(defaults.VREDIS_WORKER_THREAD_TASK_NUM):
            Thread(target=self._thread,args=(self.cmdline_task,)).start()


_o_print = print
def _lk_print(*a,**kw):
    with common.Initer.lock:
        _o_print(*a,**kw)
__builtins__['print'] = _lk_print

