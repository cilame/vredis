import inspect

from .sender import Sender
from .worker import Worker
from .error import SenderAlreadyStarted,NotInDefaultType

class Pipe:
    def __init__(self,):
        self.sender     = None
        self.script     = ''
        self.unstart    = True
        self.settings   = {}
        self.DEBUG      = False
        self.KEEPALIVE  = False
        self.LOG_ITEM   = True

    def from_settings(self,**settings):
        # 这里的配置可以有 redis 库里面 redis 类实例化所需要的各个参数
        # 这里的配置也可以添加需要配置的 defaults 里面的各个参数，不过里面的一些参数可以动态修改，一些不能。
        if not self.unstart: 
            raise SenderAlreadyStarted('Sender must be set before the task is sent.')
        self.settings.update(settings)
        self.sender = Sender.from_settings(**self.settings)
        return self

    def connect(self, host='localhost', port=6379, password=None, db=0):
        if not self.unstart: 
            raise SenderAlreadyStarted('Sender must be set before the task is sent.')
        d = dict(
            host=host,
            port=port,
            password=password,
            db=db,
        )
        self.settings.update(d)
        self.sender = Sender.from_settings(**self.settings)
        return self

    def __call__(self, func, **plus):
        src = inspect.getsource(func)
        src = '\n'.join(filter(lambda i:not i.strip().startswith('@'), src.splitlines()))+'\n'
        self.script += src
        def _wrapper(*args, **kwargs):
            if self.unstart:
                self.sender     = self.sender if self.sender is not None else Sender()
                self.tid        = self.sender.send({'command':'script','settings':{'VREDIS_SCRIPT':self.script,
                                                                                   'DEBUG':self.DEBUG,
                                                                                   'VREDIS_KEEP_LOG_ITEM':self.LOG_ITEM,
                                                                                   'VREDIS_KEEPALIVE':self.KEEPALIVE}})
                self.unstart    = False
            if not self.KEEPALIVE:
                plus.update({'hookcrash':{i['workerid']:i['plus'] for i in self.sender.start_worker.copy()}})
            self.sender.send_execute(self.tid, func.__name__, args, kwargs, plus)
        return _wrapper




    def set(self, **plus):
        # 这里的 plus 主要是由 worker 端的需求进行的需求处理，这里暂时就不多设定了
        # 不过为了约束执行初期的异常，这里暂时需要一个临时的验证。
        _types = ['table']
        for i in plus:
            if i not in _types:
                raise NotInDefaultType('pipe.set kwargs:{}:{} must in {}'.format(plus,i,_types))
        return lambda func: self.__call__(func, **plus)

    def table(self, table):
        # 简约版的set方法，意义更加清晰一些。
        return lambda func: self.__call__(func, **{'table':table})

    def from_table(self, table, taskid=None):
        # 预计的开发在这里需要返回一个类，这个类绑定了简单的数据取出的方法。重载迭代的方法。
        pass



    def queue(self, name):
        # 通过名字在 redis 上建立一个简单的queue队列，作为共享使用的队列。
        # 暂时觉得这里的实现方式不够 非侵入式，这种类型实在有点不爽
        pass

    def task_is_stop(self, taskid):
        # 分段处理时可以考虑发送多次任务。
        # 开发时，等待A任务关闭时再从A任务收集到数据的管道内获取数据拖下来进行B任务我觉得这样获取会更整洁一些
        # 不过这样有点不好的就是这种是广度优先的任务。以后再看吧。
        pass




pipe = Pipe()

__author__ = 'cilame'
__email__ = 'opaquism@hotmail.com'
__github__ = 'https://github.com/cilame/vredis'