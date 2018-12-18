# 增加环境变量，仅测试使用
import os
import sys
p = os.path.split(os.getcwd())[0]
p = os.path.split(p)[0]
sys.path.append(p)




import vredis
s = vredis.Worker.from_settings(host='47.99.126.229',port=6379,password='vilame')
s.start()


