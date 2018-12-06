import redis
from threading import Thread, RLock
import socket
import time

# 需要 “可配置” 的能够使用 redis 连接的类
# 直接传入字典进行实例化，或者通过 from_settings 这种方式来实现
class Initer:

    lock = RLock()

    @classmethod
    def redis_from_settings(cls, **kw):

        # 这里的字典完全就是 redis.StrictRedis 对象的所有默认参数
        d = dict(
            host='localhost',
            port=6379,
            db=0,
            password=None,
            socket_timeout=None,
            socket_connect_timeout=None,
            socket_keepalive=None, 
            socket_keepalive_options=None,
            connection_pool=None, 
            unix_socket_path=None,
            encoding='utf-8', 
            encoding_errors='strict',
            charset=None, 
            errors=None,
            decode_responses=False, 
            retry_on_timeout=False,
            ssl=False, 
            ssl_keyfile=None, 
            ssl_certfile=None,
            ssl_cert_reqs=None, 
            ssl_ca_certs=None,
            max_connections=None
        )

        # 自己设定的参数，方便与默认参数区分开
        mysettings = dict(
            socket_timeout=30,
            socket_connect_timeout=30,
            retry_on_timeout=True,
        )
        d.update(mysettings)

        # 配置 redis 链接参数
        for i in kw:
            if i in d:
                d[i] = kw[i]

        return redis.StrictRedis(**d)

    def start(self, prefix='process_'):
        # 通过函数前缀将函数以线程的方式打开。
        for proc in dir(self):
            if proc.startswith(prefix):
                Thread(target = getattr(self,proc)).start()
