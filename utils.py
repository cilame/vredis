import sys
import inspect

from common import Initer # 锁是唯一的，从这里去拿即可
lock = Initer.lock

__org_stdout__ = sys.stdout
__org_stderr__ = sys.stderr


class stdhooker:
    def __init__(self,hook=None,keep_consolelog=True):
        self.keep_consolelog = keep_consolelog
        self.cache = {} # 行缓存，一个 taskid 拥有一个行缓冲区
        assert hook.lower() in ['stdout','stderr']
        self.__org_func__ = __org_stdout__ if hook.lower() == 'stdout' else __org_stderr__

    def write(self,text):
        _text_taskid_ = None
        for i in inspect.stack():
            if '__very_unique_function_name__' in i[0].f_locals and 'taskid' in i[0].f_locals:
                _text_taskid_ = text, i[0].f_locals['taskid']
                break
        if _text_taskid_:
            text,taskid = _text_taskid_
            if taskid not in self.cache:
                self.cache[taskid] = text
            else:
                self.cache[taskid] += text
            self._write(taskid)
        else:
            if self.keep_consolelog:
                self.__org_func__.write(text)

    def _write(self,taskid):
        if '\n' in self.cache[taskid]:
            _text = self.cache[taskid].split('\n',1)
            if len(_text) == 1:
                self.cache[taskid] = ''
                with lock:
                    prefix = '[{}] '.format(taskid)
                    _text_ = _text[0] + '\n'
                    self.__org_func__.write(prefix + _text_)
            else:
                self.cache[taskid] = _text[1]
                with lock:
                    prefix = '[{}] '.format(taskid)
                    _text_ = _text[0] + '\n'
                    self.__org_func__.write(prefix + _text_)

    def flush(self):
        if self.keep_consolelog:
            self.__org_func__.flush()

    # 防止字典键存放 key（taskid）数量过高，每次 stop 锁住检查一次是否全部爬虫停止，若停止，执行该函数
    def _clear_cache(self):
        self.cache = {}

_stdout = stdhooker('stdout')
_stderr = stdhooker('stderr')

def hook_console(stdout=True,stderr=True):
    if stdout: sys.stdout = _stdout
    if stderr: sys.stderr = _stderr

def unhook_console(stdout=True,stderr=True):
    if stdout: sys.stdout = __org_stdout__
    if stderr: sys.stderr = __org_stderr__






