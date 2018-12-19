import redis

import re
import time
import json
import logging
import random

from . import defaults
from . import common
from .pipeline import from_pipeline, send_to_pipeline_execute
from .utils import checked_order, check_connect_worker

class Sender(common.Initer):
    def __init__(self,
            rds = redis.StrictRedis(),
        ):
        self.rds             = rds

        self.rds.ping() # 确认链接 redis。

        self.taskstop       = False
        self.start_worker   = []

    @classmethod
    def from_settings(cls,**kw):
        rds = cls.redis_from_settings(**kw)
        # 默认配置也可以在这里配置
        global defaults
        for i in kw: 
            if hasattr(defaults,i):
                setattr(defaults,i,kw[i])
        return cls(rds=rds)


    def process_run(self):
        workernum = len(self.start_worker)
        while True and workernum:
            runinfo = from_pipeline(self, self.taskid, 'run')
            if runinfo and runinfo['piptype'] == 'realtime':
                print(runinfo['msg']) # 从显示的角度来看，这里只显示 realtime 的返回，数据放在管道里即可。
            if self.taskstop and runinfo is None:
                break
        print('task stop.') # 任务结束后要打印任务执行的状态，任务执行状态的结构也需要好好考虑一下。


    def process_stop(self):

        def log_start():
            print('[ORDER]:')
            print(re.sub('"VREDIS_SCRIPT": "[^\n]+"', '"VREDIS_SCRIPT": "..."',json.dumps(self.order, indent=4)))
            assert self.order['order']['settings'] is not None
            if 'VREDIS_SCRIPT' in self.order['order']['settings']:
                print('[SCRIPT]:')
                print('\n{}'.format(self.order['order']['settings']['VREDIS_SCRIPT']))
            limit = self.order['order']['settings']['VREDIS_LIMIT_LOG_WORKER_NUM'] if 'VREDIS_LIMIT_LOG_WORKER_NUM' \
                        in self.order['order']['settings'] else defaults.VREDIS_LIMIT_LOG_WORKER_NUM
            print('[TASK]:')
            t = ['taskid:{}'.format(self.taskid),'receive worker num:{}'.format(self.pubnum)]
            if limit < self.pubnum:
                t.append('  <over VREDIS_LIMIT_LOG_WORKER_NUM:{} limited quantities.>'.format(limit))
                t.append('  <use from_settings funciton set the parameter VREDIS_LIMIT_LOG_WORKER_NUM to see more.>')
            T = True
            for idx,info in enumerate(self.start_worker):
                if T and idx >= limit:
                    T = False
                    t.append('start workerid: ...') # 超过指定数量的的任务名不显示。
                if T: t.append('start workerid:{}'.format(info['workerid']))
            print(json.dumps(t, indent=4))

        log_start()
        workerids = [i['workerid']for i in self.start_worker.copy()]
        while True and not self.taskstop:
            stopinfo = from_pipeline(self, self.taskid, 'stop')
            if stopinfo and 'taskid' in stopinfo:
                workerids.remove(stopinfo['workerid'])
            elif not workerids:
                self.taskstop = True
            else:
                for workerid in workerids:
                    if not check_connect_worker(self.rds, workerid):
                        print('unknown crash error stop workerid:{}'.format(workerid))
                        workerids.remove(workerid)

    # 通过一个队列来接受状态回写
    def send_status(self):
        start_worker = []
        for _ in range(self.pubnum):
            worker = from_pipeline(self, self.taskid, 'start')
            if worker:
                if worker['msg'] is None:
                    start_worker.append(worker)
                else:
                    # 在 start 阶段如果 msg 内有数据的话，那么就是开启时出现了错误。进行开始阶段的错误回写即可。
                    print(worker['msg'])
        self.start_worker = start_worker
        if self.start_worker:
            self.start() # 开启debug状态将额外开启两个线程作为输出日志的同步
        else:
            print('none worker receive task.')


    def send(self, input_order):
        
        def wait_connect_pub_sender(self):
            rname = '{}:{}'.format(defaults.VREDIS_PUBLISH_SENDER, self.taskid)
            self.pub = self.rds.pubsub()
            self.pub.subscribe(rname)
            while not self.rds.pubsub_numsub(rname)[0][1]:
                time.sleep(.15)

        # 获取任务id 并广播出去，一个对象维护一个taskid
        self.taskid = self.taskid if hasattr(self,'taskid') else \
            self.rds.hincrby(defaults.VREDIS_SENDER,defaults.VREDIS_SENDER_ID)
        self.order  = {'taskid':self.taskid, 'order':checked_order(input_order)}
        if defaults.DEBUG:
            wait_connect_pub_sender(self) # 发送任务前需要等待自连接广播打开,用于任意形式发送端断开能被工作端检测到
        self.pubnum = self.rds.publish(defaults.VREDIS_PUBLISH_WORKER, json.dumps(self.order))
        self.send_status()
        return self.taskid


    def send_execute(self, taskid, function_name, args, kwargs):
        if self.start_worker:
            send_to_pipeline_execute(self, taskid, function_name, args, kwargs)
