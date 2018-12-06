import redis

from threading import Thread, RLock
import json
import time
import queue
import traceback

import defaults
import common
from utils import hook_console, _stdout, _stderr
from pipline import Valve

class Worker(common.Initer):

    def __init__(self, 
            rds             = redis.StrictRedis(),
            workerid        = None
        ):
        self.rds            = rds
        self.workerid       = workerid

        self.rds.ping()
        hook_console()

        self.lock           = RLock()
        self.pub            = self.rds.pubsub()
        self.pub.subscribe(defaults.VSCRAPY_PUBLISH_WORKER)

        self.local_task     = queue.Queue()
        self.setting_task   = queue.Queue()
        self.workerid       = self.rds.hincrby(defaults.VSCRAPY_WORKER, defaults.VSCRAPY_WORKER_ID)\
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

        return cls(rds=rds,**d)

    # 检查链接状态
    def check_connect(self, taskid):
        rname = '{}:{}'.format(defaults.VSCRAPY_PUBLISH_SENDER, taskid)
        return bool(self.rds.pubsub_numsub(rname)[0][1])

    @staticmethod
    def disassemble_func(func, start=None, err=None, stop=None):
        def _disassemble(*a,**kw):
            return func, a, kw, start, err, stop
        return _disassemble

    # 开始任务
    def send_to_pipline(self, taskid, workerid, order, status=None, msg=None):
        if status is None or status.lower() not in ['start','run','stop','error']:
            raise "none init status. or status not in ['start','run','stop','error']"

        if status =='start':
            self.tasklist.add(taskid)
            _rname = '{}:{}'.format(defaults.VSCRAPY_SENDER_START, taskid)
            print('start taskid:',taskid)
        if status =='run':
            _rname = '{}:{}'.format(defaults.VSCRAPY_SENDER_RUN, taskid)
            print('run taskid:',taskid,' workerid:',workerid,' order',order)
        if status =='error':
            _rname = '{}:{}'.format(defaults.VSCRAPY_SENDER_RUN, taskid)
            print('error taskid:',taskid)
            print(msg)
        if status =='stop':
            self.tasklist.remove(taskid)
            _rname = '{}:{}'.format(defaults.VSCRAPY_SENDER_STOP, taskid)
            print('stop taskid:',taskid)
            print(' ')
        rdata = {
            'workerid': self.workerid, 
            'taskid': taskid, 
            'status': status,
            'msg':msg
        }
        self.rds.lpush(_rname, json.dumps(rdata))


    def run_until_stop(self,taskid,workerid,order):
        def _task_func(task_func):
            def pack_task(*a,**kw):
                # 给任务注入错误回调，和停止回调的函数,放进线程执行队列
                _start = self.disassemble_func(self.send_to_pipline)(taskid,workerid,order,'start')
                _error = self.disassemble_func(self.send_to_pipline)(taskid,workerid,order,'error')
                _stop  = self.disassemble_func(self.send_to_pipline)(taskid,workerid,order,'stop')
                _task  = self.disassemble_func(task_func, start=_start, err=_error, stop=_stop)\
                                              (*a,**kw)
                self.local_task.put(_task)
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
            looper      = self.run_until_stop(taskid,workerid,order)



            # 测试任务,后期需要根据 order 来实现任务处理，目前先简单实现一个函数和一个异常
            # 用以测试一般任务执行回传和错误回传
            #====================================
            def test_task(num):
                # import os
                # os.system('pip install requests')
                for i in range(num):
                    if self.check_connect(taskid): # 用来测试发送端是否断开连接的接口。检测端口还是有点耦合。
                        # 用来测试错误日志信息得回传
                        assert i<6 
                        time.sleep(.6)
                        print(i)
            #======================================


            
            test_task = looper(test_task)
            test_task(10)

    def _thread(self,local_task):
        while True:    
            func,args,kwargs,start,err,stop = local_task.get()
            def task(func,args,kwargs,start,err,stop):
                # 为了使 stack 寻找时候定位当前的环境从而找到 taskid 来分割不同任务的日志环境
                # 需要确保这里的 locals() 空间内拥有该函数名并且其余更深的环境没有该函数名字
                # 具体使用详细见 utils 内的 hook 类的函数实现（听不懂就算了，总之就是很神奇）
                __very_unique_function_name__ = func
                taskid      = start[1][0]
                workerid    = start[1][1]
                order       = start[1][2]['order']
                try:
                    if start is not None:
                        start_callback,a,kw,_,_,_ = start
                        start_callback(*a,**kw)
                    __very_unique_function_name__(*args,**kwargs)
                except Exception as e:
                    if err is not None:
                        err_callback,a,kw,_,_,_ = err
                        err_callback(*a,**kw,msg=traceback.format_exc())
                finally:
                    if stop is not None:
                        stop_callback,a,kw,_,_,_ = stop
                        stop_callback(*a,**kw)
                        with self.lock:
                            if not self.tasklist:
                                _stdout._clear_cache()
                                _stderr._clear_cache()
            task(func,args,kwargs,start,err,stop)

    def process_run_task(self):
        for i in range(defaults.VSCRAPY_WORKER_THREAD_NUM):
            Thread(target=self._thread,args=(self.local_task,)).start()

    # 动态配置需额外开启另一条线程执行，防止线程池卡死时无法进行配置的情况。
    def run_task_by_annotherthread(self):
        for i in range(defaults.VSCRAPY_WORKER_SETTING_THREAD_NUM):
            Thread(target=self._thread,args=(self.setting_task,)).start()

if __name__ == '__main__':
    wk = Worker.from_settings(host='47.99.126.229',password='vilame')
    wk.start()
