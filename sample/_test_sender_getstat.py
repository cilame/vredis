# 增加环境变量，仅测试使用
import os
import sys
p = os.path.split(os.getcwd())[0]
sys.path.append(p)




from vredis import pipe

pipe.connect(host='47.99.126.229',port=6379,password='vilame')
while 1: 
    try:
        pipe.get_stat(int(input('in:')))
    except:
        import traceback
        print(traceback.format_exc())
