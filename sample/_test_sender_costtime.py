# 增加环境变量，仅测试使用
import os
import sys
p = os.path.split(os.getcwd())[0]
sys.path.append(p)
from _test_config import host,password




from vredis import pipe

pipe.connect(host=host,port=6379,password=password)
pipe.DEBUG = True # worker端是否进行控制台打印。(默认False)
pipe.DUMPING = False # 是否进行item数据本地存储。(默认False)
pipe.KEEPALIVE = True # 是否保持链接，如果是，worker 端将监控发送端是否链接，若是 sender 端断开则停止任务。（默认True）

# 被包装的函数在 worker 端执行时，
# 返回的数据不为 None 的话，
# 1 如果是一般数据类型，会以字典的方式装包并自动 put 进默认表里。
# 2 如果是可迭代的话，会在迭代出来后，以字典的方式装包并自动 put 进默认表里。

t = False

@pipe.table('fooltable')
def some(i,t):
    if i%50==0 and t: raise # 测试异常
    import time, random
    rd = random.randint(1,2)
    #time.sleep(rd)
    if t: print('use func:{}, rd time:{}'.format(i,rd))
    yield 123,rd

@pipe
def some2(i,t):
    if i%50==0 and t: raise # 测试异常
    yield [333333,'你好']

for i in range(1):
    #print(i)
    some2(i,t)
    some(i,t)

# 被包装的函数对象将自动增加一个datas的方法，直接获取数据迭代器
# 直接迭代获取数据，如果任务未停止将会无限迭代下去。
# for i in some.datas():
#     print(i)

# for j in some2.datas():
#     print(j)

# print('=========================')
