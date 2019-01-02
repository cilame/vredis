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
VREDIS_TASK = 'vredis:sender:task'
VREDIS_TASK_CACHE = 'vredis:sender:cache'
VREDIS_TASK_STATE = 'vredis:sender:state'
VREDIS_TASK_ERROR = 'vredis:sender:error'
VREDIS_TASK_TIMEOUT = 3
VREDIS_TASK_MAXRETRY = 3 # 异常发生时，任务重试的次数

# 数据传输的管道名字，和前面的管道一样，都是在运行时加上 taskid 来分割空间
VREDIS_DATA = 'vredis:data'
VREDIS_DATA_DEFAULT_TABLE = 'default'
VREDIS_DATA_TIMEOUT = 3


# type: publish
VREDIS_PUBLISH_WORKER = 'vredis:publish:worker'
VREDIS_PUBLISH_SENDER = 'vredis:publish:sender'

# 现在默认使用的就是快速提交模式，也就是锁提交任务以20个线程实现快速提交。
VREDIS_SENDER_THREAD_SEND = 20

# “修改配置” 的任务将会在非任务线程中实现。
# 执行任务的线程数量，为防止线程过量导致问题，暂时是使用线程来实现功能。
# 不过这里的配置已经是非常重要的 worker 全局配置了。
# 当 “正在执行” 的任务数到达16时（.._PULL_NUM），第17个任务的 stop_callback 将开新线程。防止任务的线程池不够用。
# 暂时没想过如果 “正在执行” 的task任务数量过高的情况下的限制。
VREDIS_WORKER_THREAD_TASK_NUM = 17
VREDIS_WORKER_THREAD_RUN_NUM = 32

VREDIS_WORKER_IDLE_TIME = 2
VREDIS_WORKER_WAIT_STOP = 1

# 命令的类型，用来简单的约束开发
# 放弃之前的大部分考虑，现在发现一个 cmdline 就已经能够满足大部分的需求了。
VREDIS_COMMAND_TYPES = ['cmdline','script'] 
VREDIS_COMMAND_STRUCT = {'command','subcommand','settings'}

# 广播命令的传递结构是 {'command': <str> ,'subcommand': <dict> ,'settings': <dict> }
# 其中关于 script 的传递需要通过 settings 进行配置，但是 settings 内部的参数有阀门类进行管制
# 所以考虑到这一点，这边需要在 defaults 里面添加一个 VREDIS_SCRIPT 的参数来管理方便处理
# 并且要注意的是，尽量在后续开发时候，不要让配置内容的接口变成分开传递，会有问题。
VREDIS_SCRIPT = None
VREDIS_CMDLINE = None

# 队列过多时，脚本发送的日志默认只显示前10条 workerid，如需显示更多的 workerid 需要修改这里。
# 不过要检查 worker 的状态不应该在任务执行提交时检查，最好用 list 去检查会获取更多信息
VREDIS_LIMIT_LOG_WORKER_NUM = 10

# 开启 DEBUG 状态会让调试时 worker 监控 VREDIS_PUBLISH_SENDER 的链接状态
# 目前如果为 True，将覆盖 VREDIS_KEEP_LOG_CONSOLE 为 True。暂无更多影响。
DEBUG = False

# 提交任务的方法有两种类型，一种是提交之后就不必保持链接
VREDIS_KEEPALIVE = True
VREDIS_HOOKCRASH = None # 考虑到 task 隔离的问题，这里添加了这个参数来对任务空间进行配置。
VREDIS_DELAY_CLEAR = 5

# 实时回写控制台日志
# 随机选择一个任务进行实时日志回写，“随机N个”和“指定taskid或指定workerid”互斥。
# 当指定 taskid 和 workerid 进行过滤输出时，“随机选择N个”的配置就会失效
# 如果这里不设置的话，就默认是全部
VREDIS_KEEP_LOG_CONSOLE = False # 是否保持 worker 端的命令行执行。
VREDIS_KEEP_LOG_ITEM = False # 是否需要打印收集到的数据
VREDIS_FILTER_LOG_RANDOM_N = False # 现在默认关闭，暂时没时间开发
VREDIS_FILTER_LOG_TASKID = None
VREDIS_FILTER_LOG_WORKERID = None

# 用以过滤执行的任务，默认是全部都执行任务
# 注意，执行任务和执行回写是两个不同配置，请注意。
VREDIS_FILTER_TASKID = None
VREDIS_FILTER_WORKERID = None






