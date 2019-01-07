import inspect
import time
import json
import queue
import os
from threading import Thread, RLock


from . import defaults
from .sender import Sender
from .worker import Worker
from .error import SenderAlreadyStarted,NotInDefaultType



class _Table:
    def __init__(self, sender, taskid, table, method, ignore_stop=False, limit=-1):
        self.sender = sender
        self.taskid = taskid
        self.table  = table
        self.method = method
        self.limit  = limit
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
            return
        lens = lens if self.limit == -1 else min(lens, self.limit)
        if self.method == 'pop':
            for _ in range(lens):
                _, ret = self.sender.rds.brpop(table, defaults.VREDIS_DATA_TIMEOUT)
                yield json.loads(ret)
        elif self.method == 'range':
            # 对于 range 方法取数据必须要切割去取，否则当 data 数据过多时取数据会卡住任务。
            # 所以这里以 500 为一个缓冲区进行切割取数据。这个参数后续要不要暴露出去就看心情吧，
            # 因为感觉配置参数太多了。
            splitnum = 500
            q = []
            for i in range(int(lens/splitnum)):
                v = [i*splitnum, i*splitnum+splitnum] if i==0 else [i*splitnum+1, i*splitnum+splitnum]
                q.append(v)
            if lens%splitnum != 0:
                if q:
                    q.append([q[-1][-1]+1, q[-1][-1]+lens%splitnum-1])
                else:
                    q.append([0,lens-1])
            else:
                q[-1][-1] = q[-1][-1] - 1
            for start,end in q:
                for ret in self.sender.rds.lrange(table,start,end):
                    yield json.loads(ret)


class Pipe:
    def __init__(self,):
        self.sender     = None
        self.script     = ''
        self.unstart    = True
        self.settings   = self.get_config_from_homepath()
        self.timestamp  = time.time()

        self.DEBUG      = False
        self.KEEPALIVE  = True
        self.LOG_ITEM   = False
        self.QUICK_SEND = True

        self.taskqueue  = queue.Queue()
        self.lock       = RLock()


    def get_config_from_homepath(self):
        defaults_conf = dict(
            host='localhost',
            port=6379,
            password=None,
            db=0,
        )
        try:
            home = os.environ.get('HOME')
            home = home if home else os.environ.get('HOMEDRIVE') + os.environ.get('HOMEPATH')
            config = os.path.join(home,'.vredis')
            if not os.path.exists(config):
                return {}
            else:
                with open(config,encoding='utf-8') as f:
                    defaults_conf = json.load(f)
        except:
            print('unlocal homepath.')
            defaults_conf = {}
        return defaults_conf


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
            if not self.KEEPALIVE:
                self.timestamp = time.time()
            with self.lock:
                if self.unstart:
                    self.sender = self.sender if self.sender is not None else Sender.from_settings(**self.settings)
                    self.tid    = self.sender.get_taskid()
                    self.sender.rds.hset(defaults.VREDIS_WORKER, '{}@stamp'.format(self.tid), int(time.time()))
                    if self.QUICK_SEND:
                        # 多线程池任务发送
                        self.quicker()
                        self.task_sender = self.quick_send
                    else:
                        # 单线程发送任务即可
                        self.task_sender = self.normal_send
                    if not self.KEEPALIVE:
                        # 发送模式先获取任务id号码，先传输任务
                        self.send_work_delay()
                    else:
                        # 实时模式则先发送任务，直接实时传输任务即可。
                        self.send_work()
                    self.unstart = False
            self.task_sender(self.tid, func.__name__, args, kwargs, plus, self.KEEPALIVE)
        return _wrapper




    # 线程池，主要用于快速提交任务使用
    def quicker(self):
        def _sender():
            while True:
                try:
                    taskid, function_name, args, kwargs, plus, keepalive = self.taskqueue.get(timeout=2)
                    self.sender.send_execute(taskid, function_name, args, kwargs, plus, keepalive)
                except:
                    if time.time() - self.timestamp > 2:
                        break
                    time.sleep(.15)
        for _ in range(defaults.VREDIS_SENDER_THREAD_SEND):
            Thread(target=_sender).start()

    # 快速提交任务，如果你不是实时任务模式的话，就没有必要慢慢的跑任务 DEBUG
    def quick_send(self, taskid, function_name, args, kwargs, plus, keepalive):
        self.taskqueue.put((taskid, function_name, args, kwargs, plus, keepalive))

    def normal_send(self, taskid, function_name, args, kwargs, plus, keepalive):
        self.sender.send_execute(taskid, function_name, args, kwargs, plus, keepalive)




    # 开启任务
    def send_work(self):
        self.tid =  self.sender.send(input_order = {
                        'command':'script',
                        'settings':{
                            'VREDIS_SCRIPT':        self.script,
                            'DEBUG':                self.DEBUG,
                            'VREDIS_KEEP_LOG_ITEM': self.LOG_ITEM,
                            'VREDIS_KEEPALIVE':     self.KEEPALIVE}
                        },
                    keepalive=self.KEEPALIVE)

    # 延迟开启任务
    def send_work_delay(self):
        # 如果无需保持连接的话，等执行完就
        def _logtoggle():
            while time.time() - self.timestamp < 1.5: # 当任务发送结束（间隙不超过）n秒后就开始从日志管道抽取日志信息。
                time.sleep(.15)
            self.send_work()
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

    def from_table(self, taskid, table=defaults.VREDIS_DATA_DEFAULT_TABLE, method='range', limit=-1):
        # 预计的开发在这里需要返回一个类，这个类绑定了简单的数据取出的方法。重载迭代的方法。
        # limit 参数只能在 method=range 情况下才能使用。
        assert method in ['pop', 'range']
        if self.sender is None:
            host = self.settings.get('host','localhost')
            port = self.settings.get('port',6379)
            print('[ INFO ]: use defaults host:{}, port:{}.'.format(host,port))
        self.sender = self.sender if self.sender is not None else Sender.from_settings(**self.settings)
        return _Table(self.sender, taskid, table, method, limit=limit)


    def get_stat(self, taskid):
        if self.sender is None:
            host = self.settings.get('host','localhost')
            port = self.settings.get('port',6379)
            print('[ INFO ]: use defaults host:{}, port:{}.'.format(host,port))
        self.sender = self.sender if self.sender is not None else Sender.from_settings(**self.settings)
        v = self.sender.get_stat(taskid)
        if v is None:
            print('no stat taskid:{}.'.format(taskid))
        else:
            for i in v.items():
                print(i)
















pipe = Pipe()

__author__ = 'cilame'
__version__ = '1.1.4'
__email__ = 'opaquism@hotmail.com'
__github__ = 'https://github.com/cilame/vredis'