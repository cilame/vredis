from error import NotInDefaultsSetting
import defaults


# 这里暂定有两个功能需要实现
# 1 任务设定阀门
#   监听修改（优先级较低）# 或许可以考虑都通过任务那条线来实现
# 2 管道传输的规范化



# Valve 类用于管理默认设定下的阀门
# 通过 taskid,workerid 实例化后可以当作一个局部的 defaults 设定来使用，没有设定的都用默认设定
class Valve:
    class NoneObject: pass
    # 需要全局处理的开关村都存放在这里
    __valves__ = {}
    def __init__(self,taskid,workerid,groupid=None):
        self.__dict__['keyid'] = 't{}:w{}'.format(taskid,workerid) if groupid is None else groupid
        Valve.__valves__[self.keyid] = {}

    def __setattr__(self,attr,value):
        if hasattr(defaults,attr):
            Valve.__valves__[self.keyid][attr] = value
        else:
            raise NotInDefaultsSetting

    def __getattr__(self,attr):
        if hasattr(defaults,attr):
            value = Valve.__valves__[self.keyid].get(attr,Valve.NoneObject)
            value = value if value is not Valve.NoneObject else getattr(defaults,attr)
            return value
        else:
            raise NotInDefaultsSetting

if __name__ == '__main__':
    v = Valve(1,2)
    s = Valve(3,4)
    print('unchange:',v.VSCRAPY_SENDER_RUN)
    print('unchange:',s.VSCRAPY_SENDER_RUN)
    v.VSCRAPY_SENDER_RUN = 333
    print('change:',v.VSCRAPY_SENDER_RUN)
    print('change:',s.VSCRAPY_SENDER_RUN)
    print(v.__valves__)