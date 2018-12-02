import redis

import time
import json
import queue

import defaults
import common

class Sender(common.Initer):
    def __init__(self,
            rds = redis.StrictRedis(),
            pip_timeout = 3
        ):
        self.rds          = rds
        self.pip_timeout  = pip_timeout

        self.rds.ping() # 确认链接 redis。

        self.taskstop       = False
        self.start_spider   = []

    @classmethod
    def from_settings(cls,**kw):

        rds = cls.redis_from_settings(**kw)

        # 类内配置，修改时与 __init__ 内的参数同时修改
        d = dict(
            pip_timeout = 3
        )
        # 默认配置，修改时注意不重名就行，内部元素都是大写字母与下划线
        global defaults

        for i in kw:
            if i in d:
                d[i] = kw[i]    
            if hasattr(defaults,i):
                setattr(defaults,i,kw[i])

        return cls(rds=rds,**d)

    def from_pipline(self, taskid, pip=None):
        # 通过管道获取回传信息
        if pip is None or pip not in ['start','run','stop']:
            raise 'none init pip name.'
        if pip == 'start': 
            rname   = '{}:{}'.format(defaults.VSCRAPY_SENDER_START, taskid)
            timeout = defaults.VSCRAPY_SENDER_TIMEOUT_START
        if pip == 'run'  : 
            rname = '{}:{}'.format(defaults.VSCRAPY_SENDER_RUN,   taskid)
            timeout = defaults.VSCRAPY_SENDER_TIMEOUT_RUN
        if pip == 'stop' : 
            rname = '{}:{}'.format(defaults.VSCRAPY_SENDER_STOP,  taskid)
            timeout = defaults.VSCRAPY_SENDER_TIMEOUT_STOP
        try:
            _, ret = self.rds.brpop(rname, timeout)
            rdata = json.loads(ret) # ret 必是一个 json 字符串。
        except:
            rdata = None
        return rdata


    # 通过一个队列来接受状态回写
    def send_status(self):
        self.status_start()
        if defaults.DEBUG: self.start() # 开启debug状态将额外开启两个线程作为输出日志的同步


    def status_start(self):
        # 状态记录: 开启状态的记录
        # TODO 零检查，如果结果是零就打印配置状态，否则直接开始检查任务状态，用的 redis 队列获取
        print('send order:', self.order)
        print('receive spider num:', self.pubnum)
        with self.lock:
            start_spider = []
            for _ in range(self.pubnum):
                spider = self.from_pipline(self.taskid, 'start')
                start_spider.append(spider)
                print('spider start:',spider)
        self.start_spider = start_spider


    def process_run(self):
        spidernum = len(self.start_spider)
        while True and not self.taskstop and spidernum:
            runinfo = self.from_pipline(self.taskid, 'run')
            if runinfo:
                print('runinfo',runinfo)
        print('all task stop.')


    def process_stop(self):
        spidernum = len(self.start_spider)
        idx = 0
        over_break = 2
        while True and not self.taskstop and spidernum:
            if idx == spidernum:
                self.taskstop = True
                break
            stopinfo = self.from_pipline(self.taskid, 'stop')
            if stopinfo and 'taskid' in stopinfo and stopinfo['taskid'] != defaults.VSCRAPY_HEARTBEAT_TASK:
                idx += 1
                print('spider stop:',stopinfo)
            else:
                over_break -= 1
                if over_break == 0: # 防止 dead spider 影响停止
                    alivespidernum = self.rds.pubsub_numsub(defaults.VSCRAPY_PUBLISH_WORKER)[0][1]
                    if idx == alivespidernum: 
                        print('spidernum:',spidernum)
                        print('alivespidernum:',alivespidernum)
                        spidernum = alivespidernum

    def process_connect(self):
        # 用于通知任务发布者的连接状态,一旦这边执行完毕链接,广播连接数自动为零
        # 实现 DEBUG 状态下 spider 随时通过这边的关闭就停止
        ltime = 0
        rname = '{}:{}'.format(defaults.VSCRAPY_PUBLISH_SENDER,self.taskid)
        self.pub = self.rds.pubsub()
        self.pub.subscribe(rname)
        if ltime < time.time():
            self.rds.publish(rname,'heartbeat')
            ltime = time.time() + defaults.VSCRAPY_HEARTBEAT_TIME
        time.sleep(.15)


    def send(self, input_order):
        def check_order(order):
            # TODO 优先本地的 order 首次正确性验证
            return order

        # 获取任务id 并广播出去
        self.taskid = self.rds.hincrby(defaults.VSCRAPY_SENDER,defaults.VSCRAPY_SENDER_ID)
        self.order  = {'taskid':self.taskid, 'order':check_order(input_order)}
        self.pubnum = self.rds.publish(defaults.VSCRAPY_PUBLISH_WORKER, json.dumps(self.order))
        self.send_status()
                


if __name__ == '__main__':
    sender = Sender.from_settings(host='47.99.126.229',password='vilame')
    sender.send({123:321})