# 增加环境变量
import os
import sys
p = os.path.split(os.getcwd())[0]
p = os.path.split(p)[0]
sys.path.append(p)




import vredis
@vredis.pipe
def some(i):
    import time, random
    rd = random.randint(1,2)
    time.sleep(rd)
    print('use func:{}, rd time:{}'.format(i,rd))

for i in range(1000):
    some(i)

# import inspect
# def func(*a,**kw):
#     print('use func print:',a,kw)
# s = vredis.Sender()
# tid = s.send({'command':'script','settings':{'VREDIS_SCRIPT':inspect.getsource(func)}})

# for i in range(100):
#     s.send_execute(tid, 'func', (i,), {'qqq':333})
