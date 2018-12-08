import redis

import time
import json
import logging
import random

import defaults
import common
from error import (
    NotInDefaultCommand,
    MustDictType,
    MustInSubcommandList,
    MustInCommandList
)
from pipline import from_pipline

class Sender(common.Initer):
    def __init__(self,
            rds = redis.StrictRedis(),
            realtime = True,
            realtime_one = None,
            realtime_on_random_one = True,
            realtime_list = None
        ):
        self.rds             = rds
        self.realtime        = True
        self.realtime_one    = realtime_one        
        self.realtime_rdmone = realtime_on_random_one
        self.realtime_list   = realtime_list

        self.rds.ping() # 确认链接 redis。

        self.taskstop       = False
        self.start_worker   = []

    @classmethod
    def from_settings(cls,**kw):

        rds = cls.redis_from_settings(**kw)

        # 类内配置，后续需要增加动态修改的内容，实现动态配置某类参数
        # 暂时觉得这里的配置之后都不太可能会被用到
        d = dict(
            realtime = True,
            realtime_one = None,
            realtime_on_random_one = True,
            realtime_list = None
        )

        # 默认配置，修改时注意不重名就行，内部元素都是大写字母与下划线
        global defaults
        for i in kw:
            if i in d:
                d[i] = kw[i]    
            if hasattr(defaults,i):
                setattr(defaults,i,kw[i])

        return cls(rds=rds,**d)


    def process_run(self):
        # 这里是主要的数据回显的地方。暂时不能很好的设计命令会写的方式。
        # 命令里面如何与会写联系稍微没有设计好，需要赶紧解决。
        workernum = len(self.start_worker)

        if self.realtime_one:
            lis = [self.realtime_one]
        elif self.realtime_list:
            lis = self.realtime_list
        elif self.realtime_rdmone:
            lis = [random.choice(self.start_worker)['workerid']]
        else:
            lis = []

        def realtime_filter_by_workerid_list(workerid_list,text):
            _workerid_list  = list(map(int,workerid_list))
            _workerid       = int(text[text.find(':')+1:text.find(']')])
            if _workerid in _workerid_list:
                return True

        while True and workernum:
            runinfo = from_pipline(self, self.taskid, 'run')
            if runinfo:
                if runinfo['piptype'] == 'realtime':
                    if realtime_filter_by_workerid_list(lis, runinfo['msg']):
                        print(runinfo['msg'])
                else:
                    pass
                    #print('runinfo',runinfo) # 这里考虑本地问题持久化
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
            stopinfo = from_pipline(self, self.taskid, 'stop')
            if stopinfo and 'taskid' in stopinfo:
                idx += 1
                over_break = defaults.VSCRAPY_OVER_BREAK
                # print('worker stop:',stopinfo)
            else:
                if over_break == 1: # 防止 dead worker 影响停止
                    aliveworkernum = self.rds.pubsub_numsub(defaults.VSCRAPY_PUBLISH_WORKER)[0][1]
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
            worker = from_pipline(self, self.taskid, 'start')
            if worker:
                if worker['msg'] is None:
                    start_worker.append(worker)
                else:
                    # 在 start 阶段如果 msg 内有数据的话，那么就是开启时出现了错误。
                    print(worker['msg'])
        self.start_worker = start_worker
        print(self.start_worker)

        if defaults.DEBUG and self.start_worker:
            self.start() # 开启debug状态将额外开启两个线程作为输出日志的同步


    def send(self, input_order):
        
        def wait_connect_pub(self):
            rname = '{}:{}'.format(defaults.VSCRAPY_PUBLISH_SENDER, self.taskid)
            self.pub = self.rds.pubsub()
            self.pub.subscribe(rname)
            self.rds.publish(rname,'heartbeat')
            while not self.rds.pubsub_numsub(rname)[0][1]:
                time.sleep(.15)

        def checked_order(order):
            # 异常、类型检查

            def check_command(order, subcommandlist):
                # 指令的约束，生成更规范的结构
                if 'subcommand' not in order:
                    order['subcommand'] = None
                else:
                    if type(order['subcommand']) != dict:
                        raise MustDictType('order:subcommand "{}" must be a dict type.'\
                            .format(order['subcommand']))
                    if list(order['subcommand'])[0] not in subcommandlist:
                        raise MustInSubcommandList('order:subcommand:key "{}" must in subcommandlist {}.'\
                            .format(list(order['subcommand'])[0],str(subcommandlist)))
                if 'setting' not in order:
                    order['setting'] = None
                else:
                    if type(order['setting']) != dict:
                        raise MustDictType('order:setting "{}" must be a dict type.'\
                            .format(order['setting']))
                for i in order:
                    if i not in defaults.VSCRAPY_COMMAND_STRUCT:
                        raise NotInDefaultCommand('{} not in {}'.format(i,defaults.VSCRAPY_COMMAND_STRUCT))
                return order

            if type(order) != dict:
                raise MustDictType('order "{}" must be a dict type.'\
                    .format(order))
            if 'command' not in order:
                raise 'order must has a "command" key'
            if order['command'] not in defaults.VSCRAPY_COMMAND_TYPES:
                raise MustInCommandList('{} not in {}'.format(order['command'],defaults.VSCRAPY_COMMAND_TYPES))


            # 结构检查，并填充默认值，使得传输更具备结构性
            if order['command'] == 'list':  order = check_command(order, ['alive', 'check'])
            if order['command'] == 'run':   pass # TODO
            if order['command'] == 'set':   pass
            if order['command'] == 'attach':pass
            if order['command'] == 'dump':  pass
            return order

        # 获取任务id 并广播出去
        self.taskid = self.rds.hincrby(defaults.VSCRAPY_SENDER,defaults.VSCRAPY_SENDER_ID)
        self.order  = {'taskid':self.taskid, 'order':checked_order(input_order)}
        if defaults.DEBUG:
            wait_connect_pub(self) # 发送任务前需要等待自连接广播打开,用于任意形式发送端断开能被工作端检测到
        self.pubnum = self.rds.publish(defaults.VSCRAPY_PUBLISH_WORKER, json.dumps(self.order))
        self.send_status()



    def send_console(self, consoleline):
        # 输送命令行执行的命令过去，或许有些程序需要使用控制台进行一些配置类的操作。
        # 就是一个 send 函数的简单包装。
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
    sender.send({'command':'test'})