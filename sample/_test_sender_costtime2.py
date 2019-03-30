# 增加环境变量，仅测试使用
import os
import sys
p = os.path.split(os.getcwd())[0]
sys.path.append(p)
from _test_config import host,password




from vredis import pipe

pipe.connect(host=host,port=6379,password=password)
pipe.DEBUG = False # worker端是否进行控制台打印。(默认False)
pipe.DUMPING = False # 是否进行item数据本地存储。(默认False)
pipe.KEEPALIVE = True # 是否保持链接，如果是，worker 端将监控发送端是否链接，若是 sender 端断开则停止任务。（默认True）

# 测试 exec 中的函数环境变量

@pipe.table('fooltable')
def some(i):
    print('index:',i)
    for i in range(3000):
        # print('some:',i)
        some2(i,i*i)

@pipe
def some2(a,b):
    for i in range(10):
        yield ('some2',a,b)


some(5)