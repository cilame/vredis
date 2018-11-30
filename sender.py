import redis

import time

import defaults
import common

class Sender(common.Initer):
    def __init__(self,
            rds = redis.StrictRedis(),
            order_timeout = 3
        ):
        self.rds            = rds
        self.order_timeout  = order_timeout

        self.rds.ping() # 确认链接 redis。

    @classmethod
    def from_settings(cls,**kw):

        rds = cls.redis_from_settings(**kw)

        d = dict(
            order_timeout = 3
        )
        for i in kw:
            if i in d:
                d[i] = kw[i]

        return cls(rds=rds,**d)




    def ret_rdata(self, taskid):
        rname = '{}:{}'.format(defaults.VSCRAPY_SENDER, taskid)
        try:
            _, ret = self.rds.brpop(rname, self.order_timeout)
            rdata = eval(ret) # ret 必是一个 bit的 json字符串。 eg. b"{'spider': 129, 'taskid': 141, 'status': 'run success'}"
        except:
            rdata = None
        return rdata



    # 通过一个队列来接受状态回写
    def send_status(self, taskid, num):
        # TODO 零检查，如果结果是零就打印配置状态，否则直接开始检查任务状态，用的 redis 队列获取
        with self.lock:
            ls = []
            for _ in range(num):
                rdata = self.ret_rdata(taskid)
                ls.append(rdata)
                print(rdata)

            # 这里显示开启的状态，开启一定是需要考虑状态
            print('all spider start.')

        # debug 模式开启时，这里需要不断通过 redis 队列获取日志文件，用以调试
        # with self.lock:
        #     if defaults.DEBUG:
        #         while not self.stop:
        #             # 打印日志
        #             pass


    def check_stop(self):
        pass


    def stop_by_taskid(taskid):
        # 调试异常时可以通过这个来直接停止任务
        pass


    def check_order(self, order):
        # TODO 优先本地的 order 正确性验证
        return order



    def send(self, order):
        taskid      = self.rds.hincrby(defaults.VSCRAPY_SENDER,defaults.VSCRAPY_SENDER_ID)

        # TODO 包装任务 id 广播出去
        pack_order  = {'taskid':taskid, 'order':self.check_order(order)}
        pubnum      = self.rds.publish(defaults.VSCRAPY_PUBLISH, pack_order)

        print('send order:', pack_order)
        print('send receive num:', pubnum)
        # 带锁程序
        self.send_status(taskid, pubnum)








    def reset_spider_id(self):
        self.rds.hset(defaults.VSCRAPY_SPIDER, defaults.VSCRAPY_SPIDER_ID, 0)
        # 处理这里时需要考虑让空闲的爬虫修改他们本身的 id

    # def process_keep_alive(self):
    #     # 发送者的保持链接的实现
    #     while 1:
    #         print(123)
    #         time.sleep(1)
    #     pass


if __name__ == '__main__':
    sender = Sender.from_settings(host='47.99.126.229',password='vilame')
    #sender.reset_spider_id()
    sender.send({123:321})