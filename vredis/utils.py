import sys
import inspect
from queue import Queue
from threading import Thread
#import logging

from . import common
from . import defaults
from .pipeline import (
    send_to_pipeline_real_time,
    send_to_pipeline_execute
)
from .error import (
    NotInDefaultsSetting,
    NotInDefaultCommand,
    MustDictType,
    MustInSubcommandList,
    MustInCommandList,
    UndevelopmentSubcommand,
    SettingError
)

__org_stdout__ = sys.stdout
__org_stderr__ = sys.stderr



#=======================
# 这里是 worker 端的函数
#=======================

class stdhooker:
    def __init__(self,hook=None):
        self.cache = {} # 行缓存，一个 taskid 拥有一个行缓冲区
        assert hook.lower() in ['stdout','stderr']
        self.__org_func__ = __org_stdout__ if hook.lower() == 'stdout' else __org_stderr__

    def write(self,text):
        _taskid_workerid_order_rds_valve_rdm_ = find_task_locals_by_thread()
        if _taskid_workerid_order_rds_valve_rdm_:
            taskid,workerid,order,rds,valve,rdm = _taskid_workerid_order_rds_valve_rdm_
            if taskid not in self.cache:
                self.cache[taskid] = text
            else:
                self.cache[taskid] += text
            self._write(taskid,workerid,order,rds,valve,rdm)
        else:
            self.__org_func__.write(text)

    def _write(self,taskid,workerid,order,rds,valve,rdm):
        if '\n' in self.cache[taskid]:
            _text = self.cache[taskid].rsplit('\n',1)
            self.cache[taskid] = '' if len(_text) == 1 else _text[1]
            _text_ = '[{}:{}] '.format(taskid,workerid) + _text[0]

            # 管道架设在这里，现在发现用 valve 来进行配置还挺方便的，能保证任务隔离，动态配置时候还很方便。
            if valve.VREDIS_KEEPALIVE and log_filter(taskid,workerid,valve,rdm): 
                send_to_pipeline_real_time(taskid,workerid,order,rds,_text_)
            if valve.VREDIS_KEEP_LOG_CONSOLE:
                self.__org_func__.write(_text_ + '\n')

    def flush(self):
        self.__org_func__.flush()

    def _clear_cache(self,taskid):
        if taskid in self.cache:
            self.cache.pop(taskid)

_stdout = stdhooker('stdout')
_stderr = stdhooker('stderr')

def hook_console(stdout=True,stderr=True):
    if stdout: sys.stdout = _stdout#; logging.sys.stdout = _stdout
    if stderr: sys.stderr = _stderr#; logging.sys.stderr = _stderr

def unhook_console(stdout=True,stderr=True):
    if stdout: sys.stdout = __org_stdout__#; logging.sys.stdout = __org_stdout__
    if stderr: sys.stderr = __org_stderr__#; logging.sys.stderr = __org_stderr__


# 用于挂钩功能的的核心函数
def find_task_locals_by_thread():
    _taskid_workerid_order_rds_valve_rdm_ = None
    for i in inspect.stack():
        if '__very_unique_function_name__' in i[0].f_locals and 'taskid' in i[0].f_locals:
            _taskid_workerid_order_rds_valve_rdm_ = \
                i[0].f_locals['taskid'],\
                i[0].f_locals['workerid'],\
                i[0].f_locals['order'],\
                i[0].f_locals['rds'],\
                i[0].f_locals['valve'],\
                i[0].f_locals['rdm']
            break
    return _taskid_workerid_order_rds_valve_rdm_

# 阀门过滤器1
def log_filter(taskid,workerid,valve,rdm):
    # 这里不把 find_task_locals_by_thread 函数包装进去，
    # 是因为前置需要用到 find_task_locals_by_thread 函数的返回值进行判断
    if valve.VREDIS_FILTER_LOG_RANDOM_N \
        and valve.VREDIS_FILTER_LOG_TASKID is None\
        and valve.VREDIS_FILTER_LOG_WORKERID is None:
        return rdm == 1
    else:
        if valve.VREDIS_FILTER_LOG_WORKERID is not None:
            r1 = True if workerid in valve.VREDIS_FILTER_LOG_WORKERID else False
        else:
            r1 = True
        if valve.VREDIS_FILTER_LOG_TASKID is not None:
            r2 = True if taskid in valve.VREDIS_FILTER_LOG_TASKID else False
        else:
            r2 = True
        return r1 and r2

# 阀门过滤器2
def order_filter():
    taskid,workerid,order,rds,valve,rdm = find_task_locals_by_thread()
    if valve.VREDIS_FILTER_WORKERID is not None:
        r1 = True if workerid in valve.VREDIS_FILTER_WORKERID else False
    else:
        r1 = True
    if valve.VREDIS_FILTER_TASKID is not None:
        r2 = True if taskid in valve.VREDIS_FILTER_TASKID else False
    else:
        r2 = True
    return r1 and r2

# 检查链接状态
def check_connect_sender(rds, taskid, sender_pubn):
    rname = '{}:{}'.format(defaults.VREDIS_PUBLISH_SENDER, taskid)
    #print(rds.pubsub_numsub(rname),sender_pubn)
    return bool(rds.pubsub_numsub(rname)[0][1] >= sender_pubn)

# 检查链接状态
def check_connect_worker(rds, workerid, workeridd):
    # 目前的处理方法不能稳定返回正常的连接状态，并且redis中暂未找到解决方案。
    # 所以将这里以返回True的方式锁住，以后 redis 有更好的解决方法这里再改。
    return True
    rname = '{}:{}'.format(defaults.VREDIS_PUBLISH_WORKER, workerid)
    #print(rds.pubsub_numsub(rname),workeridd)
    return bool(rds.pubsub_numsub(rname)[0][1] >= workeridd[workerid])

# # 检查某 worker的某任务的执行状态是否停止
# def check_stop_worker(rds, taskid, workerid):
#     rname = '{}@stop{}'.format(taskid, workerid)
#     return bool(rds.hget(defaults.VREDIS_WORKER, rname) or 0)






# 阀门转移到 utils 里面，因为几乎可以作为较为通用的工作来使用
# 这里暂定有两个功能需要实现
# 1 任务设定阀门
# 2 管道传输的规范化

# Valve 类用于管理默认设定下的阀门
# 通过 taskid 实例化后可以当作一个局部的 defaults 设定来使用，没有设定的都用默认设定
class Valve:
    class NoneObject: pass
    # 需要全局处理的开关村都存放在这里
    __valves__ = {}
    def __init__(self,taskid,groupid=None):
        self.__dict__['keyid'] = taskid if groupid is None else groupid
        Valve.__valves__[self.keyid] = {}

    def __setattr__(self,attr,value):
        if hasattr(defaults,attr):
            Valve.__valves__[self.keyid][attr] = value
        else:
            raise NotInDefaultsSetting('[{}] {}'.format(self.keyid,attr))

    def __getattr__(self,attr):
        if hasattr(defaults,attr):
            value = Valve.__valves__[self.keyid].get(attr,Valve.NoneObject)
            value = value if value is not Valve.NoneObject else getattr(defaults,attr)
            return value
        else:
            raise NotInDefaultsSetting('[{}] {}'.format(self.keyid,attr))

    def update(self,settings):
        if settings is not None:
            for key in settings:
                if not hasattr(defaults,key):
                    raise NotInDefaultsSetting('[{}] {}'.format(self.keyid,key))
            Valve.__valves__[self.keyid].update(settings)

    def delete(self,taskid):
        if taskid in Valve.__valves__:
            Valve.__valves__.pop(taskid)

    def clear(self):
        Valve.__valves__ = {}


funcqueue = Queue()
def quick_sender():
    def _send_in_worker():
        while True:
            taskid,funcname,args,kwargs,plus = funcqueue.get()
            send_to_pipeline_execute(TaskEnv.__worker__,taskid,funcname,args,kwargs,plus)
    for _ in range(defaults.VREDIS_SENDER_THREAD_SEND):
        Thread(target=_send_in_worker).start()
def pipefunc(taskid, funcname, plus):
    if TaskEnv.__worker__ is None:
        raise SettingError('Un Init Worker.')
    def _wrapper(*args,**kwargs):
        funcqueue.put((taskid,funcname,args,kwargs,plus))
    return _wrapper

# 任务执行环境的处理，这里的类和阀门类很类似，不过主要是用于在缓存里面存放脚本环境的一种方式
class TaskEnv:
    __taskenv__ = {}
    __worker__ = None
    def __init__(self,taskid,groupid=None,worker=None):
        self.keyid = taskid if groupid is None else groupid
        if TaskEnv.__worker__ is None:
            TaskEnv.__worker__ = worker
            quick_sender()
        if order_filter(): 
            if self.keyid not in TaskEnv.__taskenv__:
                TaskEnv.__taskenv__[self.keyid] = { 'env_local':{},
                                                    'task_local':None,
                                                    'lock':0,
                                                    'start':False,
                                                    'digest_dead':0,
                                                    'stamp':{'key':None,'value':0},}

    def mk_env_locals(__very_unique_self__, __very_unique_script__):
        if order_filter():
            # script 是一个字符串的脚本，传入之后将针对该字符串的环境进行传递
            __very_unique_dict__ = {}
            if __very_unique_script__ is not None:
                exec(__very_unique_script__ + '''
__very_unique_item__ = None
for __very_unique_item__ in locals():
    if __very_unique_item__ == '__very_unique_self__' or \
       __very_unique_item__ == '__very_unique_dict__' or \
       __very_unique_item__ == '__very_unique_script__' or \
       __very_unique_item__ == '__very_unique_item__':
           continue
    __very_unique_dict__[__very_unique_item__] = locals()[__very_unique_item__]
''')
            TaskEnv.__taskenv__[__very_unique_self__.keyid]['env_local'].update(__very_unique_dict__)

    def mk_task_locals(self, tupl):
        if order_filter():
            TaskEnv.__taskenv__[self.keyid]['task_local'] = tupl


    @staticmethod
    def get_env_locals(taskid):
        temp = TaskEnv.__taskenv__.get(taskid, {'env_local':{},
                                                'task_local':None,
                                                'lock':0,
                                                'start':False,
                                                'digest_dead':0,
                                                'stamp':{'key':None,'value':0},})
        return temp['env_local']

    @staticmethod
    def get_task_locals(taskid):
        temp = TaskEnv.__taskenv__.get(taskid, {'env_local':{},
                                                'task_local':None,
                                                'lock':0,
                                                'start':False,
                                                'digest_dead':0,
                                                'stamp':{'key':None,'value':0},})
        return temp['task_local']

    @staticmethod
    def delete(taskid):
        if taskid in TaskEnv.__taskenv__:
            TaskEnv.__taskenv__.pop(taskid)

    @staticmethod
    def clear():
        TaskEnv.__taskenv__ = {}

    @staticmethod
    def incr(rds, taskid, workerid):
        with common.Initer.lock:
            if taskid in TaskEnv.__taskenv__:
                TaskEnv.__taskenv__[taskid]['lock'] += 1
                if not TaskEnv.__taskenv__[taskid]['start']:
                    TaskEnv.__taskenv__[taskid]['start'] = True
            _nlock = '{}@lock{}'.format(taskid, workerid)
            v = rds.hincrby(defaults.VREDIS_WORKER, _nlock, amount=1)
            #__org_stdout__.write('{}::{}\n'.format(v, TaskEnv.__taskenv__[taskid].get('lock')))

    @staticmethod
    def decr(rds, taskid, workerid):
        with common.Initer.lock:
            if taskid in TaskEnv.__taskenv__:
                TaskEnv.__taskenv__[taskid]['lock'] -= 1
            _nlock = '{}@lock{}'.format(taskid, workerid)
            v = rds.hincrby(defaults.VREDIS_WORKER, _nlock, amount=-1)
            #__org_stdout__.write('{}::{}\n'.format(v, TaskEnv.__taskenv__[taskid].get('lock')))

    @staticmethod
    def stamp_times(stamp, taskid):
        if stamp != TaskEnv.__taskenv__[taskid]['stamp']['key']:
            TaskEnv.__taskenv__[taskid]['stamp']['key'] = stamp
            TaskEnv.__taskenv__[taskid]['stamp']['value'] = 1
        else:
            TaskEnv.__taskenv__[taskid]['stamp']['value'] += 1
        return TaskEnv.__taskenv__[taskid]['stamp']['value']

    @staticmethod
    def idle(rds, taskid, workerid, valve):
        # 看着非常恶心的安全措施代码。
        if taskid in TaskEnv.__taskenv__:
            _cstop = '{}@stop{}'.format(taskid, workerid)
            _llock = '{}@lock{}'.format(taskid, workerid)
            _cache = '{}:{}:{}'.format(defaults.VREDIS_TASK_CACHE, taskid, workerid)

            if TaskEnv.__taskenv__[taskid]['start'] == False:
                TaskEnv.__taskenv__[taskid]['digest_dead'] += 1
                if TaskEnv.__taskenv__[taskid]['digest_dead'] > 5:
                    # 连续超过 5 次idle判断都未启动则代表线程可能处于卡死状态，自动销毁
                    # 不过这种的处理场景不多(例如一个任务n个线程跑，总会有n-1个线程空跑，所以需要处理)
                    #print('disconnect task:{}, worker:{}.'.format(taskid,workerid))
                    return True 

            if TaskEnv.__taskenv__[taskid]['start']:
                llock = int(rds.hget(defaults.VREDIS_WORKER, _llock) or 0) # 这应该是最后最后的抗灾回收处理了。
                if TaskEnv.__taskenv__[taskid]['lock'] == 0 or llock == 0:
                    m, n = 0, 0
                    if valve.VREDIS_HOOKCRASH is None: return False
                    for workerid in valve.VREDIS_HOOKCRASH:
                        # 目前发现一个严重的问题，check_connect_worker 并不一定能检测到是否连接
                        # 所以之前的大部分期望保证任务完整性的开发在这一个redis目前无法解决的问题上只能妥协
                        # 也就是说，目前将会暂时将这里用一个简单的逻辑锁住。 check_connect_worker 函数只返回True。
                        # 对于使用者来说，不能像之前那样期望从断线的 worker 的任务缓冲中回收任务了。
                        # 不过，现在就只是要保证 worker 端尽量稳定开启状态了。等以后redis解决问题后再考虑修改检查方法。
                        if not check_connect_worker(rds, workerid, valve.VREDIS_HOOKCRASH):
                            _rname = '{}:{}'.format(defaults.VREDIS_TASK, taskid)
                            _cname = '{}:{}:{}'.format(defaults.VREDIS_TASK_CACHE, taskid, workerid)
                            while rds.llen(_cname) != 0:
                                n += 1
                                rds.brpoplpush(_cname, _rname, defaults.VREDIS_TASK_TIMEOUT)
                        else:
                            _nlock = '{}@lock{}'.format(taskid, workerid)
                            m += int(rds.hget(defaults.VREDIS_WORKER, _nlock) or 0)
                    toggle = m == 0 and n == 0
                    if toggle:
                        return toggle

                    # 以下是针对网络情况不佳的一种极端情况的处理。
                    # 连续超过N次 stamp 不变，就开始考虑清理各个缓存空间，防止任务堆积
                    # 这是最后的异常处理，是没有办法的办法！因为不可控的网络问题可能存在缓冲区没有自我清空
                    # 那么最后就由自身进行对全部任务的清空处理，这样会导致部分任务重复收集，
                    # 但是从数量上看非常有限，对数据的收集没有大影响。至少为了不漏缺收集数据，这些处理都很有必要。
                    _stamp = '{}::{}'.format(m,n)
                    _stime = TaskEnv.stamp_times(_stamp, taskid)
                    # print(_stamp,_stime)
                    if _stime > 6:
                        if _stime > 8:
                            return True
                        for workerid in valve.VREDIS_HOOKCRASH:
                            if not check_connect_worker(rds, workerid, valve.VREDIS_HOOKCRASH):
                                _rname = '{}:{}'.format(defaults.VREDIS_TASK, taskid)
                                _cname = '{}:{}:{}'.format(defaults.VREDIS_TASK_CACHE, taskid, workerid)
                                _nlock = '{}@lock{}'.format(taskid, workerid)
                                while rds.llen(_cname) != 0:
                                    rds.brpoplpush(_cname, _rname, defaults.VREDIS_TASK_TIMEOUT)
                                rds.hset(defaults.VREDIS_WORKER, _nlock, 0)
                        





#=======================
# 这里是 sender 端的函数
#=======================

def checked_order(order):
    # 异常、类型检查，并且补充指令的结构进行传输
    # 基础的指令结构为 {'command': <str> ,'subcommand': <dict> ,'settings': <dict> }


    def defaults_settings(order):
        # 针对不同指令实现不同的默认参数配置
        # 开发时可以通过这里的配置防止各个默认状态的配置交叉感染

        order['settings'] = {} if order['settings'] is None else order['settings']
        debug = order['settings']['DEBUG'] if 'DEBUG' in order['settings'] else defaults.DEBUG
        if order['command'] == 'list':
            d = dict(
                VREDIS_KEEP_LOG_CONSOLE         = bool(debug),  # 默认关闭，是否保持工作端的打印输出 
                VREDIS_FILTER_LOG_RANDOM_N      = False,
                # 默认关闭，如果没有设置过滤的 taskid或 workerid，是否随机选N个回显
                # 若关闭，且未设置过滤列表（任务id或工作id）则回写全部
                # defaults 里面也是默认关闭这项的，这项主要是用于单独调试脚本，
                # 多个任务同时回写看上去很乱，这只是为了一个更简化的个人使用方式。
                # 这里写出来就是提醒一下存在这个可以配置的参数而已。
                # 现在考虑了一下，感觉实际用处不大，后续这个参数将作为可有可无的废弃状态。
            )
        elif order['command'] == 'cmdline':
            d = dict(
                VREDIS_KEEP_LOG_CONSOLE         = bool(debug),
            )
        elif order['command'] == 'attach':
            # TODO 后续根据实际情况配置
            d = dict(
                VREDIS_KEEP_LOG_CONSOLE         = bool(debug),
            )
        elif order['command'] == 'script':
            # TODO 后续根据实际情况配置
            d = dict(
                VREDIS_KEEP_LOG_CONSOLE         = bool(debug),    # 脚本的传递
            )
        else:
            d = {}
        d.update(order['settings']); order['settings'] = d
        return order


    def check_command(order, subcommandlist=None):
        # 指令的约束，生成更规范的结构
        # 指令有哪些 subcommand 可以通过在这里进行异常的约束
        if subcommandlist:
            if 'subcommand' not in order:
                order['subcommand'] = None
            else:
                if type(order['subcommand']) != dict:
                    raise MustDictType('order:subcommand "{}" must be a dict type.'\
                        .format(order['subcommand']))
                if list(order['subcommand'])[0] not in subcommandlist:
                    raise MustInSubcommandList('order:subcommand:key "{}" must in subcommandlist {}.'\
                        .format(list(order['subcommand'])[0],str(subcommandlist)))
        else:
            # 没有 subcommandlist 参数的话，这里将会默认将 subcommand key填充 None 保证结构
            # 由于 subcommandlist 是开发者来选填的部分，所以这里的开发部分注意
            if 'subcommand' not in order:
                order['subcommand'] = None
            else:
                raise UndevelopmentSubcommand('{}, check your subcommand.'.format(order['subcommand']))
        if 'settings' not in order:
            order['settings'] = None
        else:
            if type(order['settings']) != dict:
                raise MustDictType('order:settings "{}" must be a dict type.'\
                    .format(order['settings']))
        for i in order:
            if i not in defaults.VREDIS_COMMAND_STRUCT:
                raise NotInDefaultCommand('{} not in {}'.format(i,defaults.VREDIS_COMMAND_STRUCT))
        return defaults_settings(order)

    if type(order) != dict:
        raise MustDictType('order "{}" must be a dict type.'\
            .format(order))
    if 'command' not in order:
        raise 'order must has a "command" key'
    if order['command'] not in defaults.VREDIS_COMMAND_TYPES:
        raise MustInCommandList('{} not in {}'.format(order['command'],defaults.VREDIS_COMMAND_TYPES))


    # 结构检查，并填充默认值，使得传输更具备结构性
    # 后续需要在这里配置默认参数的传递，防止只用一个 defaults 配置时无法对交叉的默认参数进行应对。
    if order['command'] == 'cmdline':   order = check_command(order)
    if order['command'] == 'script':    order = check_command(order)
    return order

