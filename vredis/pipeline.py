import json
import time
import types

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
        _cache = '{}:{}:{}'.format(defaults.VREDIS_TASK_CACHE, taskid, workerid)
        valve,TaskEnv = plus
        # 应该判断的是该任务下的所有 worker 是否都处理 idle状态
        # 而不是仅仅只判断本地的状态。具体的 idle 处理看 TaskEnv 类具体实现。
        if valve.VREDIS_CMDLINE is None:
            while cls.rds.llen(_cname) or not TaskEnv.idle(cls.rds, taskid, workerid, valve):
                time.sleep(defaults.VREDIS_WORKER_WAIT_STOP)
        try:
            while cls.rds.llen(_cache) != 0 or cls.rds.llen(_cname) != 0:
                time.sleep(defaults.VREDIS_WORKER_WAIT_STOP)
            if valve.VREDIS_CMDLINE is None:
                valve.delete(taskid)
            TaskEnv.delete(taskid)
            cls.tasklist.remove(taskid)
        except:
            pass
        _sname_c = '{}:{}:{}'.format(defaults.VREDIS_TASK_STATE, taskid, workerid)
        cls.rds.hincrby(_sname_c,'stop',1) # 写入停止标记
        _rname = '{}:{}'.format(defaults.VREDIS_SENDER_STOP, taskid)
        # print('stop')
    rdata = {
        'workerid': workerid, 
        'taskid': taskid, 
        'piptype': piptype,
        'msg':msg,
        'plus':plus if piptype == 'start' else None,
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
def send_to_pipeline_real_time(taskid,workerid,order,rds,msg,dumps=False):
    _rname = '{}:{}'.format(defaults.VREDIS_SENDER_RUN, taskid)
    rdata = {
        'workerid': workerid, 
        'taskid': taskid, 
        'piptype': 'realtime',
        'dumps':dumps,
        'msg':msg
    }
    rds.lpush(_rname, json.dumps(rdata))







#==========
# 任务指令
#==========

# 单片的任务指令的传递，这种只能用管道来实现才不会起执行的冲突
def from_pipeline_execute(cls, taskid):
    _rname = '{}:{}'.format(defaults.VREDIS_TASK, taskid)
    _cname = '{}:{}:{}'.format(defaults.VREDIS_TASK_CACHE, taskid, cls.workerid)
    try:
        # 通过 brpoplpush 这样的原子操作在 redis 上面制造缓冲空间，让意外断开连接不会影响任务的执行
        ret = cls.rds.brpoplpush(_rname, _cname, defaults.VREDIS_TASK_TIMEOUT)
        rdata = json.loads(ret)
    except:
        ret,rdata = None,None
    return ret,rdata

# 单片任务需要传递的就是直接执行的任务名字
def send_to_pipeline_execute(cls, taskid, function_name, args, kwargs, plus={}):
    _rname = '{}:{}'.format(defaults.VREDIS_TASK, taskid)
    sdata = {
        'taskid': taskid,
        'function': function_name,
        'args': args,
        'kwargs': kwargs,
        'plus':plus, # 额外配置
    }
    cls.rds.lpush(_rname, json.dumps(sdata))





#==========
# 数据收集
#==========
# 数据收集的方式
def from_pipeline_data(cls, taskid, table='default'):
    _rname = '{}:{}:{}'.format(defaults.VREDIS_DATA, taskid, table)
    try:
        _, ret = cls.rds.brpop(_rname, defaults.VREDIS_DATA_TIMEOUT)
        rdata = json.loads(ret) # ret 必是一个 json 字符串。
    except:
        rdata = None
    return rdata

# 数据传递需要给一个名字来指定数据的管道，因为可能一次任务中需要收集n种数据。
def send_to_pipeline_data(cls, taskid, data, ret, table='default', valve=None):
    _rname = '{}:{}:{}'.format(defaults.VREDIS_DATA, taskid, table)
    _cname = '{}:{}:{}'.format(defaults.VREDIS_TASK_CACHE, taskid, cls.workerid)
    _sname_c = '{}:{}:{}'.format(defaults.VREDIS_TASK_STATE, taskid, cls.workerid)

    if data is None:
        # 无收集数据时进行的数据清尾工作
        cls.rds.lrem(_cname, 1, ret)
        cls.rds.hincrby(_sname_c,'execute',1)
        return

    def mk_sdata(data):
        return json.dumps({'table': table, 'data': data})

    its = []
    dt = None
    lg = True if valve is not None and valve.VREDIS_DUMP_REALTIME_ITEM else False
    # 最外层返回的数据只要是list，或是tuple，那就迭代取出然后准备传入 redis。
    if isinstance(data,(types.GeneratorType,list,tuple)):
        for i in data:
            # 深层的内容可以不用考虑是否是 list 或 tuple 的向下迭代。只管传进去即可。
            if isinstance(i,(list,tuple,dict,int,str,float)):
                its.append(mk_sdata(i))
            else:
                raise NotInDefaultType('{} not in defaults type:{}.'.format(
                                type(data),'(GeneratorType,list,tuple,dict,int,str,float)'))        
    elif isinstance(data, (dict,int,str,float)):
        dt = mk_sdata(data)
    else:
        raise NotInDefaultType('{} not in defaults type:{}.'.format(
                        type(data),'(GeneratorType,list,tuple,dict,int,str,float)'))

    func = lambda i:send_to_pipeline_real_time(taskid,cls.workerid,None,cls.rds,i,dumps=True)
    n = 0
    with cls.rds.pipeline() as pipe:
        pipe.multi()
        for it in its:
            if lg: 
                func(it)
            else:
                pipe.lpush(_rname, it)
                n += 1
        if dt is not None:
            if lg:
                func(dt)
            else:
                pipe.lpush(_rname, dt)
                n += 1
        pipe.lrem(_cname, -1, ret)
        pipe.hincrby(_sname_c,'collection',n)
        pipe.hincrby(_sname_c,'execute',1)
        pipe.execute()
