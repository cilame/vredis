import sys
import inspect
import logging

from pipline import send_to_pipline_real_time

__org_stdout__ = sys.stdout
__org_stderr__ = sys.stderr


class stdhooker:
    def __init__(self,hook=None,keep_consolelog=True):
        self.keep_consolelog = keep_consolelog
        self.cache = {} # 行缓存，一个 taskid 拥有一个行缓冲区
        assert hook.lower() in ['stdout','stderr']
        self.__org_func__ = __org_stdout__ if hook.lower() == 'stdout' else __org_stderr__

    def write(self,text):
        _text_taskid_workerid_order_rds_ = None
        for i in inspect.stack():
            if '__very_unique_function_name__' in i[0].f_locals and 'taskid' in i[0].f_locals:
                _text_taskid_workerid_order_rds_ = text,\
                                                    i[0].f_locals['taskid'],\
                                                    i[0].f_locals['workerid'],\
                                                    i[0].f_locals['order'],\
                                                    i[0].f_locals['rds']
                break
        if _text_taskid_workerid_order_rds_:
            text,taskid,workerid,order,rds = _text_taskid_workerid_order_rds_
            if taskid not in self.cache:
                self.cache[taskid] = text
            else:
                self.cache[taskid] += text
            self._write(taskid,workerid,order,rds)
        else:
            if self.keep_consolelog:
                self.__org_func__.write(text)

    def _write(self,taskid,workerid,order,rds):
        if '\n' in self.cache[taskid]:
            _text = self.cache[taskid].rsplit('\n',1)
            self.cache[taskid] = '' if len(_text) == 1 else _text[1]
            _text_ = '[{}:{}] '.format(taskid,workerid) + _text[0]

            # 管道架设在这里，或许可以考虑在这里通过order来配置是否需要回传内容
            send_to_pipline_real_time(taskid,workerid,order,rds,_text_)
            self.__org_func__.write(_text_ + '\n')

    def flush(self):
        if self.keep_consolelog:
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

