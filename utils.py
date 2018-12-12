import sys
import inspect
import logging
import defaults

from pipeline import send_to_pipeline_real_time
from error import (
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
        _taskid_workerid_order_rds_valve_rdm_ = find_task_locals()
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
            if self._filter(taskid,workerid,valve,rdm): 
                send_to_pipeline_real_time(taskid,workerid,order,rds,_text_)
            if valve.VSCRAPY_KEEP_CONSOLE_LOG:
                self.__org_func__.write(_text_ + '\n')

    def _filter(self,taskid,workerid,valve,rdm):
        if valve.VSCRAPY_FILTER_RANDOM_ONE \
            and valve.VSCRAPY_FILTER_TASKID is None\
            and valve.VSCRAPY_FILTER_WORKERID is None:
            return rdm == 1
        else:
            if valve.VSCRAPY_FILTER_WORKERID is not None:
                r1 = True if workerid in valve.VSCRAPY_FILTER_WORKERID else False
            else:
                r1 = True
            if valve.VSCRAPY_FILTER_TASKID is not None:
                r2 = True if taskid in valve.VSCRAPY_FILTER_TASKID else False
            else:
                r2 = True
            return r1 and r2

    def flush(self):
        self.__org_func__.flush()

    # 防止字典键存放 key（taskid）数量过高，每次 stop 锁住检查一次是否全部爬虫停止，若停止，执行该函数
    def _clear_cache(self):
        self.cache = {}

_stdout = stdhooker('stdout')
_stderr = stdhooker('stderr')

def hook_console(stdout=True,stderr=True):
    if stdout: sys.stdout = _stdout#; logging.sys.stdout = _stdout
    if stderr: sys.stderr = _stderr#; logging.sys.stderr = _stderr

def unhook_console(stdout=True,stderr=True):
    if stdout: sys.stdout = __org_stdout__#; logging.sys.stdout = __org_stdout__
    if stderr: sys.stderr = __org_stderr__#; logging.sys.stderr = __org_stderr__




def find_task_locals():
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
    def __init__(self,taskid,workerid,groupid=None):
        self.__dict__['keyid'] = 't{}:w{}'.format(taskid,workerid) if groupid is None else groupid
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










#=======================
# 这里是 sender 端的函数
#=======================

def checked_order(order):
    # 异常、类型检查，并且补充指令的结构进行传输
    # 基础的指令结构为 {'command': <str> ,'subcommand': <dict> ,'settings': <dict> }


    def defaults_settings(order):
        order['settings'] = {} if order['settings'] is None else order['settings']
        debug = order['settings']['DEBUG'] if 'DEBUG' in order['settings'] else defaults.DEBUG
        if order['command'] == 'list':
            d = dict(
                VSCRAPY_KEEP_REALTIME_LOG = True, # 工作端执行结果实时回显，因为该命令返回数据量少所以需要全部回显
                VSCRAPY_FILTER_RANDOM_ONE = False,# 默认关闭，如果没有设置过滤的 taskid或 workerid则随机选一个回显
                VSCRAPY_KEEP_CONSOLE_LOG = False  # 默认关闭，保持工作端的打印输出
            )
        elif order['command'] == 'run':
            d = dict(
                VSCRAPY_KEEP_REALTIME_LOG = bool(debug), # DEBUG 默认则会实时回显
                VSCRAPY_FILTER_RANDOM_ONE = True, # 默认开启
                VSCRAPY_KEEP_CONSOLE_LOG = False  # 默认关闭
            )
        elif order['command'] == 'attach':
            # TODO 后续根据实际情况配置
            d = dict(
                VSCRAPY_KEEP_REALTIME_LOG = True,
                VSCRAPY_FILTER_RANDOM_ONE = False,
                VSCRAPY_KEEP_CONSOLE_LOG = False
            )
        elif order['command'] == 'dump':
            # TODO 后续根据实际情况配置
            d = dict(
                VSCRAPY_KEEP_REALTIME_LOG = True,
                VSCRAPY_FILTER_RANDOM_ONE = False,
                VSCRAPY_KEEP_CONSOLE_LOG = False
            )
        elif order['command'] == 'test':
            # TODO 后续根据实际情况配置
            d = dict(
                VSCRAPY_KEEP_REALTIME_LOG = True,
                VSCRAPY_FILTER_RANDOM_ONE = True,
                VSCRAPY_KEEP_CONSOLE_LOG = True    # 该工具开发时，worker端调试需要
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
            if i not in defaults.VSCRAPY_COMMAND_STRUCT:
                raise NotInDefaultCommand('{} not in {}'.format(i,defaults.VSCRAPY_COMMAND_STRUCT))
        return defaults_settings(order)

    if type(order) != dict:
        raise MustDictType('order "{}" must be a dict type.'\
            .format(order))
    if 'command' not in order:
        raise 'order must has a "command" key'
    if order['command'] not in defaults.VSCRAPY_COMMAND_TYPES:
        raise MustInCommandList('{} not in {}'.format(order['command'],defaults.VSCRAPY_COMMAND_TYPES))


    # 结构检查，并填充默认值，使得传输更具备结构性
    # 后续需要在这里配置默认参数的传递，防止只用一个 defaults 配置时无法对交叉的默认参数进行应对。
    if order['command'] == 'list':  order = check_command(order, ['alive', 'check'])
    if order['command'] == 'run':   pass # TODO
    if order['command'] == 'attach':order = check_command(order, ['set', 'connect'])
    if order['command'] == 'dump':  pass
    if order['command'] == 'test':  order = check_command(order)
    return order








# if __name__ == '__main__':
#     v = Valve(1,2)
#     s = Valve(3,4)
#     print('unchange:',v.VSCRAPY_SENDER_RUN)
#     print('unchange:',s.VSCRAPY_SENDER_RUN)
#     v.VSCRAPY_SENDER_RUN = 333
#     print('change:',v.VSCRAPY_SENDER_RUN)
#     print('change:',s.VSCRAPY_SENDER_RUN)
#     print(v.__valves__)