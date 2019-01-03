# 增加环境变量，仅测试使用
import os
import sys
p = os.path.split(os.getcwd())[0]
sys.path.append(p)
from _test_config import host,password




from vredis import pipe

pipe.connect(host=host,port=6379,password=password)
# 最简单的数据抽取


taskid = 26
for i in pipe.from_table(taskid):
    print(i)
# from_table 使用默认的 table 空间名字 “default”。
# 在发送任务不指定 table 空间名字就使用 default 的空间名字