import platform
from error import UndevelopmentSubcommand
from utils import order_filter


# 目前要根据 defaults.VREDIS_COMMAND_TYPES 里面的参数进行开发各自的执行指令的方式



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
def run_command(cls, taskid, workerid, order):
    # 状态问题：
    # 这一步需要很小心的开发，因为这里含有状态统计的需求，需要随时都能看到收集的状态
    # 目前打算是考虑生成一个统一的 stat 状态管理类来统一管理，像是阀门类那样进行操作即可。
    # 数据也经量放在一个能够稳定管理数据的地方
    #（目前考虑是直接放在 redis 里面，后续会兼容 mysql或sqlite3 之类的，因为 redis 崩溃会丢失数据的可能） 
    # 收集问题：
    # 默认开发是将数据放入 redis 内部管道，不过尽量开发一个可以配置直接传入其他数据库进行持久化的功能
    # 这样就更方便的直接传输数据。
    pass


@od_filter
def attach_command(cls, taskid, workerid, order):
    # 正式任务中是不需要回写的，因为会占用一部分资源，所以非 DEBUG 状态下，默认是将所有显示关闭。
    # 但是中途想要看看数据显示状态的话，就需要该处的方法，该处的方法
    pass


@od_filter
def test_command(cls, taskid, workerid, order):
    # 测试任务,后期需要根据 order 来实现任务处理，目前先简单实现一个函数和一个异常
    # 用以测试一般任务执行回传和错误回传
    # 这里直接使用taskid 可能存在问题，因为当前环境的taskid 是会动态改变的，所以当前的检测会有问题
    # 所以在脚本执行的时候需要将靠谱的环境参数也要添加进去，不然不能根据 taskid 来检测发送端的断连。
    # import os
    # v = os.popen('pip install requests')
    # print(v.read())
    # 后续内部参数类似于 num 这种参数都将会一并并入对 order 参数的处理当中。
    for i in range(200):
        if cls.check_connect(taskid): # 用来测试发送端是否断开连接的接口。检测端口还是有点耦合。
            assert i<100 #;time.sleep(.01) # 测试异常情况的回传
            print(i)