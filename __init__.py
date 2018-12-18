import inspect

from .sender import Sender
from .worker import Worker
from .error import SenderAlreadyStarted

class Pipe:
    def __init__(self,):
        self.sender  = None
        self.script  = ''
        self.unstart = True
        self.settings = {}
        self.DEBUG   = True

    def from_settings(self,**settings):
        if not self.unstart: 
            raise SenderAlreadyStarted('Sender must be set before the task is sent')
        self.settings.update(settings)
        self.sender = Sender.from_settings(**self.settings)
        return self

    def connect(self, host='localhost', port=6379, password=None, db=0):
        if not self.unstart: 
            raise SenderAlreadyStarted('Sender must be set before the task is sent')
        d = dict(
            host=host,
            port=port,
            password=password,
            db=db,
        )
        self.settings.update(d)
        self.sender = Sender.from_settings(**self.settings)
        return self

    def __call__(self, func):
        src = inspect.getsource(func)
        src = '\n'.join(filter(lambda i:not i.strip().startswith('@'), src.splitlines()))+'\n'
        self.script += src
        def _wrapper(*args, **kwargs):
            if self.unstart:
                self.sender     = self.sender if self.sender is not None else Sender()
                self.tid        = self.sender.send({'command':'script','settings':{'VREDIS_SCRIPT':self.script,'DEBUG':self.DEBUG}})
                self.unstart    = False
            self.sender.send_execute(self.tid, func.__name__, args, kwargs)
        return _wrapper

    def queue(self, name):
        # 通过名字在 redis 上建立一个简单的queue队列，作为共享使用的队列。
        pass

pipe = Pipe()