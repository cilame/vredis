import sys
import inspect
#import logging

from . import defaults
from .pipeline import send_to_pipeline_real_time
from .error import (
    NotInDefaultsSetting,
    NotInDefaultCommand,
    MustDictType,
    MustInSubcommandList,
    MustInCommandList,
    UndevelopmentSubcommand
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
            if log_filter(taskid,workerid,valve,rdm): 
                send_to_pipeline_real_time(taskid,workerid,order,rds,_text_)
            if valve.VREDIS_KEEP_LOG_CONSOLE:
                self.__org_func__.write(_text_ + '\n')

    def flush(self):
        self.__org_func__.flush()

    # 防止字典键存放 key（taskid）数量过高，每次 stop 锁住检查一次是否全部爬虫停止，若停止，执行该函数
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
    if valve.VREDIS_FILTER_LOG_RANDOM_ONE \
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
def check_connect_sender(rds, taskid):
    rname = '{}:{}'.format(defaults.VREDIS_PUBLISH_SENDER, taskid)
    return bool(rds.pubsub_numsub(rname)[0][1])

# 检查链接状态
def check_connect_worker(rds, workerid):
    rname = '{}:{}'.format(defaults.VREDIS_PUBLISH_WORKER, workerid)
    return bool(rds.pubsub_numsub(rname)[0][1])









# 阀门转移到 utils 里面，因为几乎可以作为较为通用的工作来使用
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


# 任务执行环境的处理，这里的类和阀门类很类似，不过主要是用于在缓存里面存放脚本环境的一种方式
class TaskEnv:
    __taskenv__ = {}
    def __init__(self,taskid,groupid=None):
        self.keyid = taskid if groupid is None else groupid
        if order_filter(): 
            if self.keyid not in TaskEnv.__taskenv__:
                TaskEnv.__taskenv__[self.keyid] = {'env_local':{},'task_local':None}

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
        temp = TaskEnv.__taskenv__.get(taskid, {'env_local':{},'task_local':None})
        return temp['env_local']

    @staticmethod
    def get_task_locals(taskid):
        temp = TaskEnv.__taskenv__.get(taskid, {'env_local':{},'task_local':None})
        return temp['task_local']

    @staticmethod
    def delete(taskid):
        if taskid in TaskEnv.__taskenv__:
            TaskEnv.__taskenv__.pop(taskid)

    @staticmethod
    def clear():
        TaskEnv.__taskenv__ = {}







#=======================
# 这里是 sender 端的函数
#=======================

def checked_order(order):
    # 异常、类型检查，并且补充指令的结构进行传输
    # 基础的指令结构为 {'command': <str> ,'subcommand': <dict> ,'settings': <dict> }


    def defaults_settings(order):
        # 针对不同指令实现不同的默认参数配置

        order['settings'] = {} if order['settings'] is None else order['settings']
        debug = order['settings']['DEBUG'] if 'DEBUG' in order['settings'] else defaults.DEBUG
        if order['command'] == 'list':
            d = dict(
                VREDIS_KEEP_LOG_CONSOLE         = bool(debug),  # 默认关闭，是否保持工作端的打印输出 
                VREDIS_FILTER_LOG_RANDOM_ONE    = False,
                # 默认关闭，如果没有设置过滤的 taskid或 workerid，是否随机选一个回显
                # 若关闭，且未设置过滤列表（任务id或工作id）则回写全部
                # defaults 里面也是默认关闭这项的，这项主要是用于单独调试脚本，
                # 多个任务同时回写看上去很乱，这只是为了一个更简化的个人使用方式。
                # 这里写出来就是提醒一下存在这个可以配置的参数而已。
            )
        elif order['command'] == 'run':
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
    if order['command'] == 'list':  order = check_command(order, ['alive', 'check'])
    if order['command'] == 'run':   pass # TODO
    if order['command'] == 'attach':order = check_command(order, ['set', 'connect'])
    if order['command'] == 'script':order = check_command(order)
    return order

