import redis

from threading import Thread, RLock
import json
import time
import queue
import traceback
import logging

from . import defaults
from . import common
from .utils import (
    hook_console, 
    _stdout, 
    _stderr, 
    Valve, 
    TaskEnv,
)
from .pipeline import (
    send_to_pipeline,
    from_pipeline_execute,
)
from .order import (
    list_command,
    run_command,
    attach_command,
    script_command,
    test_command,
)

class Worker(common.Initer):

    def __init__(self, 
            rds             = redis.StrictRedis(),
            workerid        = None
        ):
        self.rds            = rds

        self.rds.ping()
        hook_console()

        self.lock           = RLock()
        self.pub            = self.rds.pubsub()
        self.pub.subscribe(defaults.VREDIS_PUBLISH_WORKER)

        self.pull_task      = queue.Queue()
        self.setting_task   = queue.Queue()
        self.workerid       = self.rds.hincrby(defaults.VREDIS_WORKER, defaults.VREDIS_WORKER_ID)\
                                if workerid is None else workerid

        self.tasklist       = set()

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

    # 检查链接状态
    def check_connect(self, taskid):
        rname = '{}:{}'.format(defaults.VREDIS_PUBLISH_SENDER, taskid)
        return bool(self.rds.pubsub_numsub(rname)[0][1])

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
                _start = self.disassemble_func(send_to_pipeline)(self,taskid,workerid,order,'start')
                _error = self.disassemble_func(send_to_pipeline)(self,taskid,workerid,order,'error')
                _stop  = self.disassemble_func(send_to_pipeline)(self,taskid,workerid,order,'stop')
                _task  = self.disassemble_func(task_func,start=_start,err=_error,stop=_stop)(*a,**kw)
                _queue.put(_task)
            return pack_task
        return _task_func


    def process_order(self):
        print('open worker id:',self.workerid)
        for i in self.pub.listen():
            # 过滤订阅信息
            if i['type'] == 'subscribe': continue
            order       = json.loads(i['data'])
            workerid    = self.workerid
            taskid      = order['taskid']
            order       = order['order']
            pull_looper = self.connect_work_queue(self.pull_task,   taskid,workerid,order)
            sett_looper = self.connect_work_queue(self.setting_task,taskid,workerid,order)
            global list_command,run_command,attach_command,test_command

            if   order['command'] == 'list':  pull_looper(list_command)  (self,taskid,workerid,order)
            elif order['command'] == 'run':   pull_looper(run_command)   (self,taskid,workerid,order)
            elif order['command'] == 'attach':pull_looper(attach_command)(self,taskid,workerid,order)
            elif order['command'] == 'script':pull_looper(script_command)(self,taskid,workerid,order)
            elif order['command'] == 'test':  pull_looper(test_command)  (self,taskid,workerid,order)

    def _thread(self,_queue):
        while True:
            func,args,kwargs,start,err,stop = _queue.get()
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
                except Exception as e:
                    if err is not None:
                        err_callback,a,kw,_,_,_ = err
                        err_callback(*a,**kw,msg=traceback.format_exc())
                    valve.delete(taskid)
                    TaskEnv.delete(taskid)
                finally:
                    self.rds.hdel(defaults.VREDIS_WORKER, taskid)
                    if stop is not None:
                        stop_callback,a,kw,_,_,_ = stop
                        stop_callback(*a,**kw)
                    _stdout._clear_cache(taskid)
                    _stderr._clear_cache(taskid)
                    # valve.delete(taskid) 该处不应该直接删除，因为该线程属于配置线程
                    # taskenv.delete(taskid)
            task(func,args,kwargs,start,err,stop)


    def _thread_run(self):
        # 这里需要考虑怎么实现环境的搭建和处理了。
        while True:
            #with common.Initer.lock: print(TaskEnv.__taskenv__)
            if TaskEnv.__taskenv__:
                ret = from_pipeline_execute(self, list(TaskEnv.__taskenv__))
                if ret:
                    taskid      = ret['taskid']
                    func_name   = ret['function'] # 抽取传递过来的函数名字
                    args        = ret['args']
                    kwargs      = ret['kwargs']

                    func_str    = '{}(*{},**{})'.format(func_name,args,kwargs)
                    taskenv     = TaskEnv.get_env_locals(taskid)

                    # 魔法参数，以及魔法的 task_locals，用于挂钩标准输出流
                    __very_unique_function_name__ = None
                    taskid,workerid,order,rds,valve,rdm = TaskEnv.get_task_locals(taskid)
                    if valve.DEBUG and self.check_connect(taskid):
                        exec(func_str,None,taskenv)
                    else:
                        # 这是为了考虑 redis 的存储量所做的队列清空处理
                        continue
                else:
                    time.sleep(defaults.VREDIS_WORKER_IDLE_TIME)
            else:
                time.sleep(defaults.VREDIS_WORKER_IDLE_TIME)
            



    # 用于将广播的任务信号拖拽下来进行环境配置的线程群
    def process_pull_task(self):
        for i in range(defaults.VREDIS_WORKER_THREAD_PULL_NUM):
            Thread(target=self._thread,args=(self.pull_task,)).start()

    # 直接执行任务的线程群
    def process_run_task(self):
        for i in range(defaults.VREDIS_WORKER_THREAD_RUN_NUM):
            Thread(target=self._thread_run).start()

    # 动态配置需额外开启另一条线程执行，防止线程池卡死时无法进行配置的情况。
    # 这里暂时是没有被用到的，后续再开发时候在处理
    # def process_run_set(self):
    #     for i in range(defaults.VREDIS_WORKER_THREAD_SETTING_NUM):
    #         Thread(target=self._thread,args=(self.setting_task,)).start()


_o_print = print
def _lk_print(*a,**kw):
    with common.Initer.lock:
        _o_print(*a,**kw)
__builtins__['print'] = _lk_print


if __name__ == '__main__':
    wk = Worker.from_settings(host='localhost')
    wk.start()
