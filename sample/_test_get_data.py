# 增加环境变量，仅测试使用
import os
import sys
p = os.path.split(os.getcwd())[0]
sys.path.append(p)




from vredis import pipe

pipe.connect(host='47.99.126.229',port=6379,password='vilame')
# 最简单的数据抽取

taskid = 26
for i in pipe.from_table(taskid):
    print(i)
