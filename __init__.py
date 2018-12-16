import inspect

from .sender import Sender
from .worker import Worker

sender = Sender()

def pipe(func):
    global sender
    src = inspect.getsource(func)
    src = '\n'.join(filter(lambda i:not i.strip().startswith('@'), src.splitlines()))+'\n'
    tid = sender.send({'command':'script','settings':{'VREDIS_SCRIPT':src}})
    def _func(*a,**kw):
        sender.send_execute(tid, func.__name__, a, kw)
    return _func

