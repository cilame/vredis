# type: hmap, id 自增作为 taskid
VREDIS_SENDER = 'vredis:sender'
VREDIS_SENDER_ID = 'id'

# 用来对爬虫状态的执行进行控制的，信号管道
VREDIS_SENDER_START = 'vredis:sender:start'
VREDIS_SENDER_RUN   = 'vredis:sender:run'
VREDIS_SENDER_STOP  = 'vredis:sender:stop'
VREDIS_SENDER_TIMEOUT_START = 3
VREDIS_SENDER_TIMEOUT_RUN   = 1
VREDIS_SENDER_TIMEOUT_STOP  = 2


# type: hmap, id 自增作为 workerid
VREDIS_WORKER = 'vredis:worker'
VREDIS_WORKER_ID = 'id'
# 后续在程序中增加 VREDIS_WORKER + 'taskid' 作为一个自增的数字key，
# 用以实现随机抽取一个进行回写的动作选择


# 广播的任务的处理和队列任务的处理不一样。需要考虑怎么解决问题。
VREDIS_TASK = 'vredis:task'
VREDIS_TASK_TIMEOUT = 3

# 数据传输的管道名字，和前面的管道一样，都是在运行时加上 taskid 来分割空间
VREDIS_DATA = 'vredis:data'
VREDIS_DATA_DEFAULT_TABLE = 'default'
VREDIS_DATA_TIMEOUT = 3


# type: publish
VREDIS_PUBLISH_WORKER = 'vredis:publish:worker'
VREDIS_PUBLISH_SENDER = 'vredis:publish:sender'

# “修改配置” 的任务将会在非任务线程中实现。
# 执行任务的线程数量，为防止线程过量导致问题，暂时是使用线程来实现功能。
# 不过这里的配置已经是非常重要的 worker 全局配置了。
VREDIS_WORKER_THREAD_PULL_NUM = 5
VREDIS_WORKER_THREAD_RUN_NUM = 20
VREDIS_WORKER_THREAD_SETTING_NUM = 3

VREDIS_WORKER_IDLE_TIME = 2
VREDIS_WORKER_WAIT_STOP = 1

# 命令的类型，用来简单的约束开发
# 分别代表：
# list   列出接收广播worker，
    # alive 简单的检查存活状态，目前只返回平台信息，后续可能会配置获取更多信息。
    # check 后续可能会改名字，因为预计是想用来实现检查各个任务执行的当前状态信息。用以统计。
# run    执行任务，执行那种提交形式的任务（不会对本机的链接挂钩）。
# attach 接入某个任务队列，修改其日志输出模式，让其向任务端传入日志，
    # set 由于使用场景不多，替换该功能层级，作为 attach 的一个部分，
    # connect 也将包含该功能，作为其 attach 两个下数功能之一的带参数的功能部。
# 增加 script 的指令，这个功能主要是用于将脚本环境的传递
VREDIS_COMMAND_TYPES = ['list','run','attach','script'] 
VREDIS_COMMAND_STRUCT = {'command','subcommand','settings'}

# 广播命令的传递结构是 {'command': <str> ,'subcommand': <dict> ,'settings': <dict> }
# 其中关于 script 的传递需要通过 settings 进行配置，但是 settings 内部的参数有阀门类进行管制
# 所以考虑到这一点，这边需要在 defaults 里面添加一个 VREDIS_SCRIPT 的参数来管理方便处理
# 并且要注意的是，尽量在后续开发时候，不要让配置内容的接口变成分开传递，会有问题。
VREDIS_SCRIPT = None

VREDIS_LIMIT_LOG_WORKER_NUM = 10

# 开启 DEBUG 状态会让调试时 worker 监控 VREDIS_PUBLISH_SENDER 的链接状态
# 目前如果为 True，将覆盖 VREDIS_KEEP_LOG_CONSOLE 为 True。暂无更多影响。
DEBUG = True

# 实时回写控制台日志
# 随机选择一个任务进行实时日志回写，“随机一个”和“指定taskid或指定workerid”互斥。
# 当指定 taskid 和 workerid 进行过滤输出时，“随机选择一个”的配置就会失效
# 如果这里不设置的话，就默认是全部
VREDIS_KEEP_LOG_CONSOLE = False # 是否保持 worker 端的命令行执行。
VREDIS_FILTER_LOG_RANDOM_ONE = False # 现在默认关闭，因为感觉这个功能很鸡肋，可有可无
VREDIS_FILTER_LOG_TASKID = None
VREDIS_FILTER_LOG_WORKERID = None

# 用以过滤执行的任务，默认是全部都执行任务
# 注意，执行任务和执行回写是两个不同配置，请注意。
VREDIS_FILTER_TASKID = None
VREDIS_FILTER_WORKERID = None






