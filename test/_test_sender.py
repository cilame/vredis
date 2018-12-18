# 增加环境变量，仅测试使用
import os
import sys
p = os.path.split(os.getcwd())[0]
p = os.path.split(p)[0]
sys.path.append(p)




from vredis import pipe

pipe.connect(host='47.99.126.229',port=6379,password='vilame')
pipe.DEBUG = True # worker端是否进行控制台打印。

@pipe
def some(i):
    import time, random
    rd = random.randint(1,2)
    time.sleep(rd)
    print('use func:{}, rd time:{}'.format(i,rd))

@pipe
def some2(i):
    print('use func2:{}'.format(i))

for i in range(1000):
    some(i)
    some2(i)


