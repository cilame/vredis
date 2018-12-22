# 增加环境变量，仅测试使用
import os
import sys
p = os.path.split(os.getcwd())[0]
sys.path.append(p)




from vredis import pipe

pipe.connect(host='47.99.126.229',port=6379,password='vilame')
#pipe.from_settings(VREDIS_LIMIT_LOG_WORKER_NUM=2) # 队列过多时默认只显示前10条workerid，如需显示完整需要修改这里。
pipe.DEBUG = True # worker端是否进行控制台打印。(默认False)
pipe.LOG_ITEM = False # 是否进行item数据打印显示。(默认False)

# 被包装的函数在 worker 端执行时，
# 返回的数据不为 None 的话，
# 1 如果是一般数据类型，会以字典的方式装包并自动 put 进默认表里。
# 2 如果是可迭代的话，会在迭代出来后，以字典的方式装包并自动 put 进默认表里。

@pipe
def some(i):
    import time, random
    rd = random.randint(1,2)
    time.sleep(rd)
    print('use func:{}, rd time:{}'.format(i,rd))
    return 123

@pipe
def some2(i):
    print('use func2:{}'.format(i))

for i in range(100):
    some2(i)
    some(i)


# @pipe
# def req_baidu(key='123',num=0):
#     import requests
#     from lxml import etree
#     url = 'http://www.baidu.com/s?wd={}&pn={}0'.format(key,num)
#     s = requests.get(url)
#     e = etree.HTML(s.content)
#     print(num)
#     for href in e.xpath('//div[contains(@class,"c-container")]/h3/a/@href'):
#         yield {'num':num,'href':href}

# for i in range(1000):
#     req_baidu(num=i)
