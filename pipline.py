import json

from error import NotInDefaultsSetting
import defaults

# 收发函数的统一管理
# 以下两个函数均服务于对 worker 端口信息回传的处理
# 原本都是类内函数，但是为了统一管理和维护放在这里方便管道对应处理处理
# 这里是发送端口，用于从 worker 发送到
def send_to_pipline(cls, taskid, workerid, order, piptype=None, msg=None):
    if piptype is None or piptype.lower() not in ['start','run','stop','error']:
        raise "none init piptype. or piptype not in ['start','run','stop','error']"
    if piptype =='start':
        cls.tasklist.add(taskid)
        _rname = '{}:{}'.format(defaults.VSCRAPY_SENDER_START, taskid)
        print('start')
    if piptype =='run':
        _rname = '{}:{}'.format(defaults.VSCRAPY_SENDER_RUN, taskid)
    if piptype =='error':
        _rname = '{}:{}'.format(defaults.VSCRAPY_SENDER_RUN, taskid)
        print(msg)
    if piptype =='stop':
        cls.tasklist.remove(taskid)
        _rname = '{}:{}'.format(defaults.VSCRAPY_SENDER_STOP, taskid)
        print('stop')
    rdata = {
        'workerid': cls.workerid, 
        'taskid': taskid, 
        'piptype': piptype,
        'msg':msg
    }
    cls.rds.lpush(_rname, json.dumps(rdata))

# 这里是接收端口，服务于 sender 类，用于接收回传信息
def from_pipline(cls, taskid, piptype=None):
    if piptype is None or piptype not in ['start','run','stop']:
        raise 'none init piptype name.'
    if piptype == 'start': 
        rname   = '{}:{}'.format(defaults.VSCRAPY_SENDER_START, taskid)
        timeout = defaults.VSCRAPY_SENDER_TIMEOUT_START
    if piptype == 'run': 
        rname = '{}:{}'.format(defaults.VSCRAPY_SENDER_RUN,   taskid)
        timeout = defaults.VSCRAPY_SENDER_TIMEOUT_RUN
    if piptype == 'stop' : 
        rname = '{}:{}'.format(defaults.VSCRAPY_SENDER_STOP,  taskid)
        timeout = defaults.VSCRAPY_SENDER_TIMEOUT_STOP
    try:
        _, ret = cls.rds.brpop(rname, timeout)
        rdata = json.loads(ret) # ret 必是一个 json 字符串。
    except:
        rdata = None
    return rdata




# 实时管道实现
# 现在发现这种实时管道确实要前面的哪个管道好用很多，上面的管道也兼顾的信号发送的任务
# 所以也不好废弃，而是兼顾在不同的功能上，先就目前这样好了。
def send_to_pipline_real_time(taskid,workerid,order,rds,msg):
    _rname = '{}:{}'.format(defaults.VSCRAPY_SENDER_RUN, taskid)
    rdata = {
        'workerid': workerid, 
        'taskid': taskid, 
        'piptype': 'realtime',
        'msg':msg
    }
    rds.lpush(_rname, json.dumps(rdata))








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