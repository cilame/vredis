# 增加环境变量，仅测试使用
import os
import sys
p = os.path.split(os.getcwd())[0]
sys.path.append(p)
from _test_config import host,password




from vredis import pipe

pipe.connect(host=host,port=6379,password=password)
pipe.DEBUG = True # worker端是否进行控制台打印。(默认False)
#pipe.DUMPING = True # 是否进行item数据本地存储。(默认False)
pipe.KEEPALIVE = False # 是否保持链接，如果是，worker 端将监控发送端是否链接，若是 sender 端断开则停止任务。（默认True）

# 被包装的函数在 worker 端执行时，
# 返回的数据不为 None 的话，
# 1 如果是一般数据类型，会以字典的方式装包并自动 put 进默认表里。
# 2 如果是可迭代的话，会在迭代出来后，以字典的方式装包并自动 put 进默认表里。


@pipe
def req_baidu(key='123',num=0):
    import requests
    from lxml import etree
    url = 'http://www.baidu.com/s?wd={}&pn={}0'.format(key,num)
    s = requests.get(url)
    e = etree.HTML(s.content)
    print(num)
    for href in e.xpath('//div[contains(@class,"c-container")]/h3/a/@href'):
        yield {'num':num,'href':href}

for i in range(400):
    req_baidu(num=i)

