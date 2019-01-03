# 增加环境变量，仅测试使用
import os
import sys
p = os.path.split(os.getcwd())[0]
sys.path.append(p)
from _test_config import host,password




import vredis
s = vredis.Worker.from_settings(host=host,port=6379,password=password)
#s = vredis.Worker()
s.start()


