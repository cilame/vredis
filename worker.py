import redis

from threading import Thread, RLock
import json
import time

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
        self.pub.subscribe(defaults.VSCRAPY_PUBLISH)

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





    def process_order(self):

        self.spiderid = self.rds.hincrby(defaults.VSCRAPY_SPIDER, defaults.VSCRAPY_SPIDER_ID)
        print('start spider id:',self.spiderid)

        # 配置编号的方式一类的处理
        # 用以处理后续需要的分区管理之类的扩展
        
        for i in self.pub.listen():
            if i['type'] == 'subscribe': continue
            order = eval(i['data'])
            rname = '{}:{}'.format(defaults.VSCRAPY_SENDER, order['taskid'])


            # 发送开启状态


            # TODO 处理任务（处理任务不应该在发送开启状态之前。
            # 因为要考虑到状态变化情况，所以不能简单传一个字典回去就OK。后续考虑结构后再做修改。
            # do something costime
            # time.sleep(5) # 4 test


            # 返回的数据强制规定成为一个 json 格式的数据，这样方便管理
            # 后续也需要考虑各种执行状态的情况
            rdata = {
                'spider':self.spiderid, 
                'taskid':order['taskid'], 
                'status':'run success'
            }

            self.rds.lpush(rname, rdata)
            print(order['taskid'], 'run success')



            # 执行结束后
            # 发送结束状态



    def process_keep_alive(self):
        # 主要是处理保持与广播的链接状态，一旦广播者断开链接
        # 则进行对某些关键参数的修改
        # 用于开发者对 debug 功能的检测处理
        return







if __name__ == '__main__':
    wk = Worker.from_settings(host='47.99.126.229',password='vilame')
    wk.start()
