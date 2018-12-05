import redis

from threading import Thread, RLock
import json
import time
import queue
import traceback

import defaults
import common
from utils import hook_console

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
        self.workerid       = self.rds.hincrby(defaults.VSCRAPY_WORKER, defaults.VSCRAPY_WORKER_ID)

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
    def disassemble_func(func, err=None, stop=None):
        def _disassemble(*a,**kw):
            return func,a,kw,err,stop
        return _disassemble

    # 开始任务
    def send_to_pipline(self, workerid, taskid, status=None, msg=None):
        if status is None or status.lower() not in ['start','run','stop','error']:
            raise "none init status. or status not in ['start','run','stop','error']"

        if status =='start':
            _rname = '{}:{}'.format(defaults.VSCRAPY_SENDER_START, taskid)
        if status =='run' or status=='error':
            _rname = '{}:{}'.format(defaults.VSCRAPY_SENDER_RUN, taskid)
        if status =='stop': 
            _rname = '{}:{}'.format(defaults.VSCRAPY_SENDER_STOP, taskid)
        rdata = {
            'workerid': self.workerid, 
            'taskid': taskid, 
            'status': status,
            'msg':msg
        }
        self.rds.lpush(_rname, json.dumps(rdata))


    def process_order(self):
        print('open worker id:',self.workerid)
        for i in self.pub.listen():
            # 过滤订阅信息
            if i['type'] == 'subscribe': continue
            order       = json.loads(i['data'])
            workerid    = self.workerid
            taskid      = order['taskid']

            # 启动任务，发送启动信息
            self.send_to_pipline(workerid, taskid, 'start')
            # 测试任务,后期需要根据 order 来实现任务处理
            def test_task(num,workerid=None,taskid=None,order=None):
                # import os
                # os.system('pip install requests')
                for i in range(num):
                    if self.check_connect(taskid): # 用来测试发送端是否断开连接的接口。
                        # 用来测试错误日志信息得回传
                        assert i<6 
                        time.sleep(.6)
                        self.send_to_pipline(workerid,taskid,status='run')
                        print('workerid:',workerid, ',taskid:',taskid, 'order',order)
            # 给任务注入错误回调，和停止回调的函数,放进线程执行队列
            _stop  = self.disassemble_func(self.send_to_pipline)(workerid,taskid,'stop')
            _error = self.disassemble_func(self.send_to_pipline)(workerid,taskid,'error')
            _task  = self.disassemble_func(test_task, err=_error, stop=_stop)\
                                          (10, workerid=workerid, taskid=taskid, order=order)
            self.local_task.put(_task)

    def process_run_task(self):
        while True:    
            func,args,kwargs,err,stop = self.local_task.get()
            def task(func,args,kwargs,err,stop):
                # 为了使 stack 寻找时候定位当前的环境从而找到 taskid 来分割不同任务的日志环境
                # 需要确保这里的 locals() 空间内拥有该函数名并且其余更深的环境没有该函数名字
                # 具体实现详细见 utils 内的 hook 类的函数实现
                taskid = kwargs.get('taskid')
                __very_unique_function_name__ = func
                try:
                    print('start taskid:',taskid)
                    __very_unique_function_name__(*args,**kwargs)
                except Exception as e:
                    print('error taskid:',taskid)
                    print(traceback.format_exc())
                    if err is not None:
                        __very_unique_function_name__,args,kwargs,_, _ = err
                        __very_unique_function_name__(*args,**kwargs,msg=traceback.format_exc())
                finally:
                    print('stop taskid:',taskid)
                    print(' ')
                    if stop is not None:
                        __very_unique_function_name__,args,kwargs,_, _ = stop
                        __very_unique_function_name__(*args,**kwargs)
            Thread(target=task,args=(func,args,kwargs,err,stop)).start()


if __name__ == '__main__':
    wk = Worker.from_settings(host='47.99.126.229',password='vilame')
    wk.start()
