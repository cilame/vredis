

'''
# {'type': 'subscribe', 'pattern': None, 'channel': b'vscrapy:sender:order', 'data': 1}
# {'type': 'message', 'pattern': None, 'channel': b'vscrapy:sender:order', 'data': b'{123: 321}'}

# 经过测试，可以考虑使用订阅模式来考虑指令的发布和回调实现
# 类 TCP 的握手来确认函数执行的情况

import redis
import vthread

@vthread.thread
def run():
    s = redis.StrictRedis('47.99.126.229',password='vilame')

    v = s.pubsub()
    v.subscribe('asdfasdf')

    for i in v.listen():
        print(i)


for i in range(3):
    run()
'''
