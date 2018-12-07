import redis

from threading import Thread, RLock
import json
import time
import queue
import traceback
import logging

import defaults
import common
from utils import hook_console, _stdout, _stderr
from pipline import Valve, send_to_pipline

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
            if hasattr(defaults,i):
                setattr(defaults,i,kw[i])

        return cls(rds=rds,**d)

    # 检查链接状态
    def check_connect(self, taskid):
        rname = '{}:{}'.format(defaults.VSCRAPY_PUBLISH_SENDER, taskid)
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
                _start = self.disassemble_func(send_to_pipline)(self,taskid,workerid,order,'start')
                _error = self.disassemble_func(send_to_pipline)(self,taskid,workerid,order,'error')
                _stop  = self.disassemble_func(send_to_pipline)(self,taskid,workerid,order,'stop')
                _task  = self.disassemble_func(task_func,start=_start,err=_error,stop=_stop)\
                                              (*a,**kw)
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
            task_looper = self.connect_work_queue(self.local_task,  taskid,workerid,order)
            sett_looper = self.connect_work_queue(self.setting_task,taskid,workerid,order)

            # 测试任务,后期需要根据 order 来实现任务处理，目前先简单实现一个函数和一个异常
            # 用以测试一般任务执行回传和错误回传
            #====================================
            # 这里直接使用taskid 可能存在问题，因为当前环境的taskid 是会动态改变的，所以当前的检测会有问题
            # 所以在脚本执行的时候需要将靠谱的环境参数也要添加进去，不然不能根据 taskid 来检测发送端的断连。
            def test_task(num):
                import os
                v = os.popen('pip install requests')
                print(v.read())
                for i in range(num):
                    if self.check_connect(taskid): # 用来测试发送端是否断开连接的接口。检测端口还是有点耦合。
                        # 用来测试错误日志信息得回传
                        rname = '{}:{}'.format(defaults.VSCRAPY_PUBLISH_SENDER, taskid)
                        assert i<100 
                        #time.sleep(.01)
                        print(i)
            #======================================

            
            test_task = task_looper(test_task)
            test_task(200)# 函数被包装后直接按照原来的样子执行即可

    def _thread(self,_queue):
        while True:
            func,args,kwargs,start,err,stop = _queue.get()
            def task(func,args,kwargs,start,err,stop):
                # 为了使 stack 寻找时候定位当前的环境从而找到 taskid 来分割不同任务的日志环境
                # 需要确保这里的 locals() 空间内拥有该函数名并且其余更深的环境没有该函数名字
                # 具体使用详细见 utils 内的 hook 类的函数实现（听不懂就算了，总之就是很神奇）
                __very_unique_function_name__ = func
                taskid      = start[1][1]
                workerid    = start[1][2]
                order       = start[1][3]['order']
                rds         = self.rds
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
    def process_run_set(self):
        for i in range(defaults.VSCRAPY_WORKER_THREAD_SETTING_NUM):
            Thread(target=self._thread,args=(self.setting_task,)).start()


if __name__ == '__main__':
    wk = Worker.from_settings(host='47.99.126.229',password='vilame')
    wk.start()
