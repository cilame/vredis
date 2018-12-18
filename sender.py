import redis

import time
import json
import logging
import random

from . import defaults
from . import common
from .pipeline import from_pipeline, send_to_pipeline_execute
from .utils import checked_order

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

        # 类内配置，后续需要增加动态修改的内容，实现动态配置某类参数
        # 暂时觉得这里的配置之后都不太可能会被用到
        d = dict()

        # 默认配置，修改时注意不重名就行，内部元素都是大写字母与下划线
        global defaults
        for i in kw:
            if i in d:
                d[i] = kw[i]    
            if hasattr(defaults,i):
                setattr(defaults,i,kw[i])

        return cls(rds=rds,**d)



    def task_is_empty(self):
        _rname = '{}:{}'.format(defaults.VREDIS_TASK, self.taskid)
        ret = self.rds.llen(_rname)
        return ret == 0


    def process_run(self):
        workernum = len(self.start_worker)
        while True and workernum:
            runinfo = from_pipeline(self, self.taskid, 'run')
            if runinfo and runinfo['piptype'] == 'realtime':
                print(runinfo['msg']) # 从显示的角度来看，这里只显示 realtime 的返回，数据放在管道里即可。
            if self.taskstop and runinfo is None and self.task_is_empty():
                break
        print('all task stop.')


    def process_stop(self):
        workernum = len(self.start_worker)
        idx = 0
        over_break = defaults.VREDIS_OVER_BREAK
        while True and not self.taskstop and workernum:
            stopinfo = from_pipeline(self, self.taskid, 'stop')
            if stopinfo and 'taskid' in stopinfo:
                idx += 1
                over_break = defaults.VREDIS_OVER_BREAK
                # print('worker stop:',stopinfo)
            elif idx == workernum:
                self.taskstop = True
                break
            else:
                if over_break == 1: # 防止 dead worker 影响停止
                    aliveworkernum = self.rds.pubsub_numsub(defaults.VREDIS_PUBLISH_WORKER)[0][1]
                    if idx == aliveworkernum and aliveworkernum < workernum:
                        print('workernum:',workernum)
                        print('aliveworkernum:',aliveworkernum)
                        workernum = aliveworkernum
                over_break -= 1

    # 通过一个队列来接受状态回写
    def send_status(self):
        
        print('send order:', self.order)
        print('receive worker num:', self.pubnum)
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

        if defaults.DEBUG and self.start_worker:
            self.start() # 开启debug状态将额外开启两个线程作为输出日志的同步


    def send(self, input_order):
        
        def wait_connect_pub(self):
            rname = '{}:{}'.format(defaults.VREDIS_PUBLISH_SENDER, self.taskid)
            self.pub = self.rds.pubsub()
            self.pub.subscribe(rname)
            self.rds.publish(rname,'heartbeat')
            while not self.rds.pubsub_numsub(rname)[0][1]:
                time.sleep(.15)

        # 获取任务id 并广播出去，一个对象维护一个taskid
        self.taskid = self.taskid if hasattr(self,'taskid') else \
            self.rds.hincrby(defaults.VREDIS_SENDER,defaults.VREDIS_SENDER_ID)
        self.order  = {'taskid':self.taskid, 'order':checked_order(input_order)}
        if defaults.DEBUG:
            wait_connect_pub(self) # 发送任务前需要等待自连接广播打开,用于任意形式发送端断开能被工作端检测到
        self.pubnum = self.rds.publish(defaults.VREDIS_PUBLISH_WORKER, json.dumps(self.order))
        self.send_status()
        return self.taskid


    def send_execute(self, taskid, function_name, args, kwargs):
        if self.start_worker:
            send_to_pipeline_execute(self, taskid, function_name, args, kwargs)
