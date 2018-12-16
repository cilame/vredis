import json

from error import NotInDefaultsSetting
import defaults

# 收发函数的统一管理
# 以下两个函数均服务于对 worker 端口信息回传的处理
# 原本都是类内函数，但是为了统一管理和维护放在这里方便管道对应处理
# 这里是发送端口，用于从 worker 发送到管道
def send_to_pipeline(cls, taskid, workerid, order, piptype=None, msg=None):
    if piptype is None or piptype.lower() not in ['start','run','stop','error']:
        raise "none init piptype. or piptype not in ['start','run','stop','error']"
    if piptype =='start':
        cls.tasklist.add(taskid)
        _rname = '{}:{}'.format(defaults.VREDIS_SENDER_START, taskid)
        # print('start')
    if piptype =='run':
        # 这里的 run 暂时没有信号传递的必要，以后都不会被用到
        _rname = '{}:{}'.format(defaults.VREDIS_SENDER_RUN, taskid)
    if piptype =='error':
        # 启动时的失败
        if taskid not in cls.tasklist:
            _rname = '{}:{}'.format(defaults.VREDIS_SENDER_START, taskid)
            print(msg)
        # 启动后的失败
        else:
            _rname = '{}:{}'.format(defaults.VREDIS_SENDER_RUN, taskid)
            print(msg)
    if piptype =='stop':
        try: cls.tasklist.remove(taskid)
        except: pass
        _rname = '{}:{}'.format(defaults.VREDIS_SENDER_STOP, taskid)
        # print('stop')
    rdata = {
        'workerid': cls.workerid, 
        'taskid': taskid, 
        'piptype': piptype,
        'msg':msg
    }
    cls.rds.lpush(_rname, json.dumps(rdata))

# 这里是接收端口，服务于 sender 类，用于接收回传信息
def from_pipeline(cls, taskid, piptype=None):
    if piptype is None or piptype not in ['start','run','stop']:
        raise 'none init piptype name.'
    if piptype == 'start': 
        rname   = '{}:{}'.format(defaults.VREDIS_SENDER_START, taskid)
        timeout = defaults.VREDIS_SENDER_TIMEOUT_START
    if piptype == 'run': 
        rname = '{}:{}'.format(defaults.VREDIS_SENDER_RUN,   taskid)
        timeout = defaults.VREDIS_SENDER_TIMEOUT_RUN
    if piptype == 'stop' : 
        rname = '{}:{}'.format(defaults.VREDIS_SENDER_STOP,  taskid)
        timeout = defaults.VREDIS_SENDER_TIMEOUT_STOP
    try:
        _, ret = cls.rds.brpop(rname, timeout)
        rdata = json.loads(ret) # ret 必是一个 json 字符串。
    except:
        rdata = None
    return rdata


# 实时管道实现
# 现在发现这种实时管道确实要前面的哪个管道好用很多，上面的管道也兼顾的信号发送的任务
# 所以也不好废弃，而是兼顾在不同的功能上，先就目前这样好了。上面的管道类更偏向于一种信号的发送。
def send_to_pipeline_real_time(taskid,workerid,order,rds,msg):
    _rname = '{}:{}'.format(defaults.VREDIS_SENDER_RUN, taskid)
    rdata = {
        'workerid': workerid, 
        'taskid': taskid, 
        'piptype': 'realtime',
        'msg':msg
    }
    rds.lpush(_rname, json.dumps(rdata))









# 单片的任务指令的传递，这种只能用管道来实现才不会起执行的冲突
def from_pipeline_execute(cls, taskid):
    if type(taskid) == list:
        _rname = ['{}:{}'.format(defaults.VREDIS_TASK,_taskid)for _taskid in sorted(taskid,reverse=True)]
    else:
        _rname = '{}:{}'.format(defaults.VREDIS_TASK, taskid)
    try:
        _, ret = cls.rds.brpop(_rname, defaults.VREDIS_TASK_TIMEOUT)
        rdata = json.loads(ret) # ret 必是一个 json 字符串。
    except:
        rdata = None
    return rdata

# 单片任务需要传递的就是直接执行的任务名字
def send_to_pipeline_execute(cls, taskid, function_name, args, kwargs):
    _rname = '{}:{}'.format(defaults.VREDIS_TASK, taskid)
    sdata = {
        'taskid': taskid,
        'function': function_name,
        'args': args,
        'kwargs': kwargs,
    }
    cls.rds.lpush(_rname, json.dumps(sdata))

