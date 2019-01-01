import platform
import subprocess

from . import common
from .error import UndevelopmentSubcommand
from .utils import (
    order_filter, 
    find_task_locals_by_thread,
    TaskEnv,
    check_connect_sender,
)


# 目前要根据 defaults.VREDIS_COMMAND_TYPES 里面的参数进行开发各自的执行指令的方式
# 装饰器，用以过滤执行的任务。与 defaults 中的 VREDIS_FILTER_TASKID 和 VREDIS_FILTER_WORKERID 配置相关
def od_filter(func):
    def _od_filter(*a,**kw):
        if order_filter():
            func(*a,**kw)
    return _od_filter

@od_filter
def cmdline_command(cls, taskid, workerid, order):
    # 暂时还不知道会不会对正在执行的任务有影响
    cmd = order['settings']['VREDIS_CMDLINE'].strip()
    if cmd.lower() == 'ls' or cmd.lower() == 'list':
        # 主要用于简单的查看功能所以就把简单的数据print一遍即可。
        info = '[ workerid ]:{}, platform:{}.'.format(workerid, platform.platform())
        print(info)
    else:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=1)
        for line in iter(p.stdout.readline, b''):
            try:
                line = line.decode('utf-8').strip()
                print(line)
            except:
                line = line.decode('gbk').strip()
                print(line)
            finally:
                # 存在无限的命令，所以这里需要靠连接状态的挂钩才能断开
                # 另外，使用下面的挂钩不能解决当执行时存在 y/n 等待的情况，
                # 会无限等待，卡死一个配置任务的 pull_task 线程。
                # 所以一般使用命令行最好就进行简单的 pip install ... -y 之类的简单而有用的命令即可。
                # 尽可能防止 y/n 出现。
                if not check_connect_sender(cls.rds, taskid, order['sender_pubn']):
                    break
        p.stdout.close()
        p.wait()

@od_filter
def script_command(cls, taskid, workerid, order):
    taskid,workerid,order,rds,valve,rdm = find_task_locals_by_thread()
    with common.Initer.lock:
        taskenv = TaskEnv(taskid)
        taskenv.mk_env_locals(valve.VREDIS_SCRIPT)
        taskenv.mk_task_locals((taskid,workerid,order,rds,valve,rdm))