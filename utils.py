import sys
import inspect
import logging
import defaults

from pipline import send_to_pipline_real_time
from error import NotInDefaultsSetting

__org_stdout__ = sys.stdout
__org_stderr__ = sys.stderr


class stdhooker:
    def __init__(self,hook=None):
        self.cache = {} # 行缓存，一个 taskid 拥有一个行缓冲区
        assert hook.lower() in ['stdout','stderr']
        self.__org_func__ = __org_stdout__ if hook.lower() == 'stdout' else __org_stderr__

    def write(self,text):
        _taskid_workerid_order_rds_valve_ = None
        for i in inspect.stack():
            if '__very_unique_function_name__' in i[0].f_locals and 'taskid' in i[0].f_locals:
                _taskid_workerid_order_rds_valve_ = find_task_locals()
                break
        if _taskid_workerid_order_rds_valve_:
            taskid,workerid,order,rds,valve = _taskid_workerid_order_rds_valve_
            if taskid not in self.cache:
                self.cache[taskid] = text
            else:
                self.cache[taskid] += text
            self._write(taskid,workerid,order,rds,valve)
        else:
            self.__org_func__.write(text)

    def _write(self,taskid,workerid,order,rds,valve):
        if '\n' in self.cache[taskid]:
            _text = self.cache[taskid].rsplit('\n',1)
            self.cache[taskid] = '' if len(_text) == 1 else _text[1]
            _text_ = '[{}:{}] '.format(taskid,workerid) + _text[0]

            toggle = self._filter(taskid,workerid,valve)
            # 管道架设在这里，现在发现用 valve 来进行配置还挺方便的，能保证任务隔离，动态配置时候还很方便。
            if valve.VSCRAPY_KEEP_REALTIME_LOG:
                if toggle: send_to_pipline_real_time(taskid,workerid,order,rds,_text_)
            if valve.VSCRAPY_KEEP_CONSOLE_LOG:
                if toggle: self.__org_func__.write(_text_ + '\n')

    def _filter(self,taskid,workerid,valve):
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
    _text_taskid_workerid_order_rds_ = None
    for i in inspect.stack():
        if '__very_unique_function_name__' in i[0].f_locals and 'taskid' in i[0].f_locals:
            _taskid_workerid_order_rds_valve_ = \
                i[0].f_locals['taskid'],\
                i[0].f_locals['workerid'],\
                i[0].f_locals['order'],\
                i[0].f_locals['rds'],\
                i[0].f_locals['valve']
            break
    return _taskid_workerid_order_rds_valve_


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
        for key in settings:
            if not hasattr(defaults,key):
                raise NotInDefaultsSetting('[{}] {}'.format(self.keyid,key))
        Valve.__valves__[self.keyid].update(settings)


if __name__ == '__main__':
    v = Valve(1,2)
    s = Valve(3,4)
    print('unchange:',v.VSCRAPY_SENDER_RUN)
    print('unchange:',s.VSCRAPY_SENDER_RUN)
    v.VSCRAPY_SENDER_RUN = 333
    print('change:',v.VSCRAPY_SENDER_RUN)
    print('change:',s.VSCRAPY_SENDER_RUN)
    print(v.__valves__)