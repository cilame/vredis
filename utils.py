import sys
import inspect

from common import Initer # 锁是唯一的，从这里去拿即可
lock = Initer.lock

__org_stdout__ = sys.stdout
__org_stderr__ = sys.stderr


class hook_stdout:
    def __init__(self,keep_consolelog=True):
        self.keep_consolelog = keep_consolelog
        self.cache = {} # 行缓存，一个 taskid 拥有一个行缓冲区

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
                __org_stdout__.write(text)

    def _write(self,taskid):
        if '\n' in self.cache[taskid]:
            _text = self.cache[taskid].split('\n',1)
            if len(_text) == 1:
                self.cache[taskid] = ''
                with lock:
                    __org_stdout__.write('[{}]'.format(taskid) + _text[0] + '\n')
            else:
                self.cache[taskid] = _text[1]
                with lock:
                    __org_stdout__.write('[{}]'.format(taskid) + _text[0] + '\n')

    def flush(self):
        if self.keep_consolelog:
            __org_stdout__.flush()


class hook_stderr:
    def __init__(self,keep_consolelog=True):
        self.keep_consolelog = keep_consolelog
        self.cache = {} # 行缓存，一个 taskid 拥有一个行缓冲区

    def write(self,text):
        _text_taskid_ = None
        for i in inspect.stack()[:10]: # 限制一下深度
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
                __org_stderr__.write(text)

    def _write(self,taskid):
        if '\n' in self.cache[taskid]:
            _text = self.cache[taskid].split('\n',1)
            if len(_text) == 1:
                self.cache[taskid] = ''
                with lock:
                    __org_stderr__.write(_text[0] + '\n')
            else:
                self.cache[taskid] = _text[1]
                with lock:
                    __org_stderr__.write(_text[0] + '\n')

    def flush(self):
        if self.keep_consolelog:
            __org_stderr__.flush()

def hook_console(stdout=True,stderr=True):
    if stdout: sys.stdout = hook_stdout()
    if stderr: sys.stderr = hook_stderr()

def unhook_console(stdout=True,stderr=True):
    if stdout: sys.stdout = __org_stdout__
    if stderr: sys.stderr = __org_stderr__






