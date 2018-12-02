import redis

from threading import Thread, RLock
import json
import time
import queue

import defaults
import common



class Worker(common.Initer):

    def __init__(self, 
            rds             = redis.StrictRedis(),
            spiderid        = None
        ):
        self.rds            = rds
        self.spiderid       = spiderid

        self.rds.ping()

        self.lock           = RLock()
        self.pub            = self.rds.pubsub()
        self.pub.subscribe(defaults.VSCRAPY_PUBLISH_WORKER)

        self.local_task     = queue.Queue()
        self.spiderid       = self.rds.hincrby(defaults.VSCRAPY_SPIDER, defaults.VSCRAPY_SPIDER_ID)

        self.tasklist       = set()

    @classmethod
    def from_settings(cls, **kw):

        rds = cls.redis_from_settings(**kw)
        d = dict(
            spiderid = None
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
    def disassemble_func(func,stop=None):
        def _disassemble(*a,**kw):
            return func,a,kw,stop
        return _disassemble

    # 开始任务
    def status_task(self, spiderid, taskid, status=None):
        if status is None or status.lower() not in ['start','run','stop']:
            raise "none init status. or status not in ['start','run','stop']"

        if status =='start':
            _status = 'start'
            _rname = '{}:{}'.format(defaults.VSCRAPY_SENDER_START, taskid)
            self.tasklist.add(taskid)
        if status =='run':   
            _status = 'run'
            _rname = '{}:{}'.format(defaults.VSCRAPY_SENDER_RUN, taskid)
        if status =='stop':  
            _status = 'stop'
            _rname = '{}:{}'.format(defaults.VSCRAPY_SENDER_STOP, taskid)
            self.tasklist.remove(taskid)
        rdata = {
            'spiderid': self.spiderid, 
            'taskid': taskid, 
            'status': _status
        }
        self.rds.lpush(_rname, json.dumps(rdata))


    def process_order(self):
        print('start spider id:',self.spiderid)
        for i in self.pub.listen():
            # 过滤订阅信息
            if i['type'] == 'subscribe': continue
            order       = json.loads(i['data'])
            spiderid    = self.spiderid
            taskid      = order['taskid']
            # 过滤心跳包
            if taskid == defaults.VSCRAPY_HEARTBEAT_TASK: continue

            # 启动任务，发送启动信息
            self.status_task(spiderid, taskid, 'start'); print(taskid, 'start success')
            # 测试任务,后期需要根据 order 来实现任务处理
            def test_task(num,spiderid=None,taskid=None,order=None):
                for i in range(num):
                    if self.check_connect(taskid):
                        time.sleep(.6)
                        self.status_task(spiderid,taskid,status='run')
                        print('spiderid:',spiderid, ',taskid:',taskid, 'order',order)
            # 给任务注入停止时执行的函数,放进线程执行队列
            _stop = self.disassemble_func(self.status_task)(spiderid,taskid,'stop')
            _task = self.disassemble_func(test_task, stop=_stop)(10,spiderid=spiderid,taskid=taskid,order=order)
            self.local_task.put(_task)

    def process_heartbeat(self):
        # 心跳包,保证接受任务的广播通道的存活
        while True:
            pack_order  = {'spiderid':self.spiderid, 'taskid':defaults.VSCRAPY_HEARTBEAT_TASK}
            pubnum      = self.rds.publish(defaults.VSCRAPY_PUBLISH_WORKER, json.dumps(pack_order))
            time.sleep(defaults.VSCRAPY_HEARTBEAT_TIME)

    def process_run_task(self):
        while True:    
            func,args,kwargs,stop = self.local_task.get()
            def task(func,args,kwargs,stop):
                try:
                    func(*args,**kwargs)
                except Exception as e:
                    print(e)
                finally:
                    taskid = kwargs.get('taskid')
                    if stop != None:
                        stop_func,args,kwargs, _ = stop
                        stop_func(*args,**kwargs)
                    print(taskid, 'stop success')
            Thread(target=task,args=(func,args,kwargs,stop)).start()


if __name__ == '__main__':
    wk = Worker.from_settings(host='47.99.126.229',password='vilame')
    wk.start()
