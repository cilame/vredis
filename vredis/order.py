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
def list_command(cls, taskid, workerid, order):
    subcommand = {'alive':'platform'} if order['subcommand'] == None else order['subcommand']
    if list(subcommand)[0] == 'alive':
        d = []
        for i in subcommand['alive'].split():
            # 目前暂时只有平台类型的回显
            if i.strip().lower() == 'platform':
                d.append(str(platform.platform()))
        ret = 'workerid:{}, platform:{}.'.format(workerid,' '.join(d))
        print(ret)

    elif list(subcommand)[0] == 'check':
        # 这里的展示需要考虑到执行状态的展示，所以需要在考虑正式任务执行的状态收集之后再对这里进行开发。
        # 功能：
        # 1 根据 taskid 检查数据状态，执行状态，开启状态，关闭状态等。
        # 2 根据 taskid 和 workerid 检查单个 workerid 对应的 taskid 的数据状态，执行状态，开启状态，关闭状态等。
        raise 'UnDevelopment, 正在开发该功能。'
    else:
        raise UndevelopmentSubcommand(list(subcommand)[0])

@od_filter
def cmdline_command(cls, taskid, workerid, order):
    # 暂时还不知道会不会对正在执行的任务有影响
    cmd = order['settings']['VREDIS_CMDLINE']
    print(cmd)
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
            if not check_connect_sender(cls.rds, taskid, order['sender_pubn']):
                break
    p.stdout.close()
    p.wait()

@od_filter
def attach_command(cls, taskid, workerid, order):
    # 正式任务中是不需要回写的，因为会占用一部分资源，所以非 DEBUG 状态下，默认是将所有显示关闭。
    # 但是中途想要看看数据显示状态的话，就需要该处的方法，该处的方法
    pass


@od_filter
def script_command(cls, taskid, workerid, order):
    taskid,workerid,order,rds,valve,rdm = find_task_locals_by_thread()
    with common.Initer.lock:
        taskenv = TaskEnv(taskid)
        taskenv.mk_env_locals(valve.VREDIS_SCRIPT)
        taskenv.mk_task_locals((taskid,workerid,order,rds,valve,rdm))