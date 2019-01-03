# 增加环境变量，仅测试使用
import os
import sys
p = os.path.split(os.getcwd())[0]
sys.path.append(p)
from _test_config import host,password




from vredis import pipe

pipe.connect(host=host,port=6379,password=password)
#pipe.from_settings(VREDIS_LIMIT_LOG_WORKER_NUM=10) # 队列过多时默认只显示前10条workerid，如需显示完整需要修改这里。
pipe.DEBUG = True # worker端是否进行控制台打印。(默认False)
#pipe.LOG_ITEM = False # 是否进行item数据打印显示。(默认False)
pipe.KEEPALIVE = True # 是否保持链接，如果是，worker 端将监控发送端是否链接，若是 sender 端断开则停止任务。（默认True）

# 被包装的函数在 worker 端执行时，
# 返回的数据不为 None 的话，
# 1 如果是一般数据类型，会以字典的方式装包并自动 put 进默认表里。
# 2 如果是可迭代的话，会在迭代出来后，以字典的方式装包并自动 put 进默认表里。

@pipe.table('some')
def some(i):
    if i%50==0: 
        print('rasie',i)
        raise # 测试异常
    import time, random
    rd = random.randint(1,2)
    #time.sleep(rd)
    print('use func:{}, rd time:{}'.format(i,rd))
    return 123

@pipe
def some2(i):
    if i%50==0: 
        print('rasie',i)
        raise # 测试异常
    #print('use func2:{}'.format(i))
    return 333333,444444

for i in range(1000):
    #print(i)
    some2(i)
    some(i)

print('=========================')
