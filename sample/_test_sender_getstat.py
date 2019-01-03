# 增加环境变量，仅测试使用
import os
import sys
p = os.path.split(os.getcwd())[0]
sys.path.append(p)
from _test_config import host,password




from vredis import pipe

pipe.connect(host=host,port=6379,password=password)
while 1: 
    try:
        pipe.get_stat(int(input('in:')))
    except:
        import traceback
        print(traceback.format_exc())
