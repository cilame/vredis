import inspect
import time
import json
from threading import Thread


from . import defaults
from .sender import Sender
from .worker import Worker
from .error import SenderAlreadyStarted,NotInDefaultType



class _Table:
    def __init__(self, sender, taskid, table, method, ignore_stop=False):
        self.sender = sender
        self.taskid = taskid
        self.table  = table
        self.method = method
        self.ignore_stop = ignore_stop

    def __iter__(self):
        if not self.ignore_stop:
            v = self.sender.get_stat(self.taskid)
            if v is None:
                print('no stat taskid:{}.'.format(self.taskid))
                raise 'cannot get stat.'
            close = True
            for key,value in v.items():
                if key != 'all':
                    if value.get('stop',0) == 0:
                        close = False
            if not close:
                raise 'unstop task.' 
                # 目前对非停止的任务进行数据抽取的话是会直接抛出异常的。
                # 因为目前开发是通过检查 redis 管道的长度来一次性抽取数据的，
                # 如果忽略任务停止的部分直接抽取可能就只能抽一部分。
                # 因为考虑到两种取数据的模式，pop模式会影响下标，所以默认未关闭暴力抛异常。
        table = '{}:{}:{}'.format(defaults.VREDIS_DATA, self.taskid, self.table)
        lens = self.sender.rds.llen(table)
        if lens == 0:
            print('no data. tablename: "{}".'.format(table))
        if self.method == 'pop':
            for _ in range(lens):
                _, ret = self.sender.rds.brpop(table, defaults.VREDIS_DATA_TIMEOUT)
                yield json.loads(ret)
        elif self.method == 'range':
            for ret in self.sender.rds.lrange(table,0,lens):
                yield json.loads(ret)


class Pipe:
    def __init__(self,):
        self.sender     = None
        self.script     = ''
        self.unstart    = True
        self.settings   = {}
        self.timestamp  = time.time()

        self.DEBUG      = False
        self.KEEPALIVE  = False
        self.LOG_ITEM   = False

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
                if not self.KEEPALIVE:
                    self._overtime_start_getbacklog()
                self.sender     = self.sender if self.sender is not None else Sender()
                self.tid        = self.sender.send(input_order = {
                                                        'command':'script',
                                                        'settings':{
                                                            'VREDIS_SCRIPT':        self.script,
                                                            'DEBUG':                self.DEBUG,
                                                            'VREDIS_KEEP_LOG_ITEM': self.LOG_ITEM,
                                                            'VREDIS_KEEPALIVE':     self.KEEPALIVE}
                                                        },
                                                    waitstart=not self.KEEPALIVE,
                                                    keepalive=self.KEEPALIVE)
                self.unstart    = False
            if not self.KEEPALIVE:
                self.timestamp = time.time()
            self.sender.send_execute(self.tid, func.__name__, args, kwargs, plus)
        return _wrapper



    def _overtime_start_getbacklog(self):
        # 开启另外的线程开始显示日志信息,如果没有 KEEPALIVE 则不需要
        def _logtoggle():
            while time.time() - self.timestamp < 1: # 当任务发送结束（间隙不超过）n秒后就开始从日志管道抽取日志信息。
                time.sleep(.15)
            self.sender.waitstart = False
        Thread(target=_logtoggle).start()


    def set(self, **plus):
        # 这里的 plus 主要是由 worker 端的需求进行的需求处理，这里暂时就不多设定了
        # 不过为了约束执行初期的异常，这里暂时需要一个临时的验证。
        # 后期拓展接口的开发，不过现在来说，直接使用 table 函数是个更加简便的方式。
        # 目前只有配置存储空间的函数。
        _types = ['table']
        for i in plus:
            if i not in _types:
                raise NotInDefaultType('pipe.set kwargs:{}:{} must in {}'.format(plus,i,_types))
        return lambda func: self.__call__(func, **plus)

    def table(self, table):
        # 简约版的配置方法，后期为了对某些功能连锁，可能会改。
        return lambda func: self.__call__(func, **{'table':table})

    def from_table(self, taskid, table=defaults.VREDIS_DATA_DEFAULT_TABLE, method='range'):
        # 预计的开发在这里需要返回一个类，这个类绑定了简单的数据取出的方法。重载迭代的方法。
        assert method in ['pop', 'range']
        if self.sender is None:
            print('[ WAINING ]: use localhost redis .')
        self.sender = self.sender if self.sender is not None else Sender()
        return _Table(self.sender, taskid, table, method)


    def task_is_stop(self, taskid):
        # 分段处理时可以考虑发送多次任务。
        # 开发时，等待A任务关闭时再从A任务收集到数据的管道内获取数据拖下来进行B任务我觉得这样获取会更整洁一些
        # 不过这样有点不好的就是这种是广度优先的任务。以后再看吧。
        pass

    def get_stat(self, taskid):
        if self.sender is None:
            print('[ WAINING ]: use localhost redis .')
        self.sender = self.sender if self.sender is not None else Sender()
        v = self.sender.get_stat(taskid)
        if v is None:
            print('no stat taskid:{}.'.format(taskid))
        else:
            for i in v.items():
                print(i)
















pipe = Pipe()

__author__ = 'cilame'
__version__ = '0.9.0'
__email__ = 'opaquism@hotmail.com'
__github__ = 'https://github.com/cilame/vredis'