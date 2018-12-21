import json
import time

from .error import NotInDefaultsSetting
from . import defaults



#==================
# 信号传递+环境配置
#==================

# 收发函数的统一管理
# 以下两个函数均服务于对 worker 端口信息回传的处理
# 原本都是类内函数，但是为了统一管理和维护放在这里方便管道对应处理
# 这里是发送端口，用于从 worker 发送到管道
def send_to_pipeline(cls, taskid, workerid, order, piptype=None, msg=None, plus=None):
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
        # 这里的停止需要考虑在消化队列为空的情况下才执行关闭
        _cname = '{}:{}'.format(defaults.VREDIS_TASK, taskid)
        valve,TaskEnv = plus
        # 应该判断的是该任务下的所有 worker 是否都处理 idle状态
        # 而不是仅仅只判断本地的状态。具体的 idle 处理看 TaskEnv 类具体实现。
        while cls.rds.llen(_cname) or not TaskEnv.idle(cls.rds, taskid, workerid): 
            time.sleep(defaults.VREDIS_WORKER_WAIT_STOP)
        try:
            # 这里暂时只考虑了命令行保持链接时挂钩的移除动作
            # 后续还需要考虑怎么提交式的任务，提交后就不管的那种
            valve.delete(taskid)
            TaskEnv.delete(taskid)
            cls.tasklist.remove(taskid)
        except:
            pass
        _rname = '{}:{}'.format(defaults.VREDIS_SENDER_STOP, taskid)
        # print('stop')
    rdata = {
        'workerid': workerid, 
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



#==========
# 实时输出
#==========

# 实时管道实现
# 现在发现这种实时管道确实要比前面的那个管道好用很多，上面的管道也兼顾的信号发送的任务
# 所以也不好废弃，而是兼顾在不同的功能上，先就目前这样好了。
# 或者换个想法，分成两个函数的原因：从功能上区别开来。（一个用于信号传递，一个用于实时传输）
# 并且上面有一个 tasklist 的实例内部参数需要通过 cls 传递。（用于判断是否在环境配置时就出现了错误）
def send_to_pipeline_real_time(taskid,workerid,order,rds,msg):
    _rname = '{}:{}'.format(defaults.VREDIS_SENDER_RUN, taskid)
    rdata = {
        'workerid': workerid, 
        'taskid': taskid, 
        'piptype': 'realtime',
        'msg':msg
    }
    rds.lpush(_rname, json.dumps(rdata))







#==========
# 任务指令
#==========

# 单片的任务指令的传递，这种只能用管道来实现才不会起执行的冲突
def from_pipeline_execute(cls, taskid):
    if type(taskid) == list:
        _rname = ['{}:{}'.format(defaults.VREDIS_TASK,_taskid)for _taskid in taskid]
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







#==========
# 数据收集
#==========
# 数据收集的方式
def from_pipeline_data(cls, taskid, name='default'):
    _rname = '{}:{}:{}'.format(defaults.VREDIS_DATA, taskid, name)
    try:
        _, ret = cls.rds.brpop(_rname, defaults.VREDIS_DATA_TIMEOUT)
        rdata = json.loads(ret) # ret 必是一个 json 字符串。
    except:
        rdata = None
    return rdata

# 数据传递需要给一个名字来指定数据的管道，因为可能一次任务中需要收集n种数据。
def send_to_pipeline_data(cls, taskid, data, name='default', valve=None):
    _rname = '{}:{}:{}'.format(defaults.VREDIS_DATA, taskid, name)
    sdata = {
        'taskid': taskid,
        'data': data,
    }
    if valve is not None and valve.VREDIS_KEEP_LOG_ITEM:
        print(sdata)
    cls.rds.lpush(_rname, json.dumps(sdata))