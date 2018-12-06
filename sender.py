import redis

import time
import json

import defaults
import common

class Sender(common.Initer):
    def __init__(self,
            rds = redis.StrictRedis(),
        ):
        self.rds          = rds

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

    def from_pipline(self, taskid, pip=None):
        # 通过管道获取回传信息
        if pip is None or pip not in ['start','run','stop']:
            raise 'none init pip name.'
        if pip == 'start': 
            rname   = '{}:{}'.format(defaults.VSCRAPY_SENDER_START, taskid)
            timeout = defaults.VSCRAPY_SENDER_TIMEOUT_START
        if pip == 'run': 
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
        print('receive worker num:', self.pubnum)
        with self.lock:
            start_worker = []
            for _ in range(self.pubnum):
                worker = self.from_pipline(self.taskid, 'start')
                start_worker.append(worker)
                print('worker start:',worker)
        self.start_worker = start_worker


    def process_run(self):
        workernum = len(self.start_worker)
        while True and workernum:
            runinfo = self.from_pipline(self.taskid, 'run')
            if runinfo:
                print('runinfo',runinfo)
            if self.taskstop and runinfo is None:
                break
        print('all task stop.')


    def process_stop(self):
        workernum = len(self.start_worker)
        idx = 0
        over_break = defaults.VSCRAPY_OVER_BREAK
        while True and not self.taskstop and workernum:
            if idx == workernum:
                self.taskstop = True
                break
            stopinfo = self.from_pipline(self.taskid, 'stop')
            if stopinfo and 'taskid' in stopinfo:
                idx += 1
                over_break = defaults.VSCRAPY_OVER_BREAK
                print('worker stop:',stopinfo)
            else:
                over_break -= 1
                if over_break == 1: # 防止 dead worker 影响停止
                    aliveworkernum = self.rds.pubsub_numsub(defaults.VSCRAPY_PUBLISH_WORKER)[0][1]
                    if idx == aliveworkernum and aliveworkernum < workernum:
                        print('workernum:',workernum)
                        print('aliveworkernum:',aliveworkernum)
                        workernum = aliveworkernum

    def wait_connect_pub(self):
        rname = '{}:{}'.format(defaults.VSCRAPY_PUBLISH_SENDER, self.taskid)
        self.pub = self.rds.pubsub()
        self.pub.subscribe(rname)
        self.rds.publish(rname,'heartbeat')
        while defaults.DEBUG and not bool(self.rds.pubsub_numsub(rname)[0][1]):
            time.sleep(.15)

    def send(self, input_order):
        def check_order(order):
            # TODO 优先本地的 order 首次正确性验证
            return order

        # 获取任务id 并广播出去
        self.taskid = self.rds.hincrby(defaults.VSCRAPY_SENDER,defaults.VSCRAPY_SENDER_ID)
        self.order  = {'taskid':self.taskid, 'order':check_order(input_order)}
        if defaults.DEBUG:
            self.wait_connect_pub() # 发送任务前需要等待自连接广播打开,用于任意形式发送端断开能被工作端检测到
        self.pubnum = self.rds.publish(defaults.VSCRAPY_PUBLISH_WORKER, json.dumps(self.order))
        self.send_status()

    def send_console(self, consoleline):
        # 输送命令行执行的命令过去，或许有些程序需要使用控制台进行一些配置类的操作。
        pass

    def check_worker_status(self, workerid=None, feature=None):
        # 通过id检查，某些工作端的状态，默认全部。一般过滤用 feature，不配置信息量会比较少
        # 执行流程就是先检查存活状态，然后通过存活的线程决定下一步怎么处理
        pass

    def check_task_status(self, taskid=None, feature=None):
        # 通过id列表来统计任务执行的状态，feature 过滤方式
        pass


if __name__ == '__main__':
    sender = Sender.from_settings(host='47.99.126.229',password='vilame')
    sender.send({123:321})