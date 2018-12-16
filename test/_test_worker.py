# 增加环境变量
import os
import sys
p = os.path.split(os.getcwd())[0]
p = os.path.split(p)[0]
sys.path.append(p)




import vredis
s = vredis.Worker()
s.start()


