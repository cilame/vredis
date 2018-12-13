# type: hmap, id 自增作为 taskid
VREDIS_SENDER = 'vredis:sender'
VREDIS_SENDER_ID = 'id'

# 用来对爬虫状态的执行进行控制的
VREDIS_SENDER_START = 'vredis:sender:start'
VREDIS_SENDER_RUN   = 'vredis:sender:run'
VREDIS_SENDER_STOP  = 'vredis:sender:stop'
VREDIS_SENDER_TIMEOUT_START = 3
VREDIS_SENDER_TIMEOUT_RUN   = 1
VREDIS_SENDER_TIMEOUT_STOP  = 3

# 处理在 sender 端同步log时出现断连接的 worker 超时处理次数
VREDIS_OVER_BREAK = 2

# type: hmap, id 自增作为 workerid
VREDIS_WORKER = 'vredis:worker'
VREDIS_WORKER_ID = 'id'
# 后续在程序中增加 VREDIS_WORKER + 'taskid' 作为一个自增的数字key，
# 用以实现随机抽取一个进行回写的动作选择

# type: publish
VREDIS_PUBLISH_WORKER = 'vredis:publish:worker'
VREDIS_PUBLISH_SENDER = 'vredis:publish:sender'

# “修改配置” 的任务将会在非任务线程中实现。
# 执行任务的线程数量，为防止线程过量导致问题，暂时是使用线程来实现功能。
# 不过这里的配置已经是非常重要的 worker 全局配置了。
VREDIS_WORKER_THREAD_NUM = 16
VREDIS_WORKER_THREAD_SETTING_NUM = 3

# 命令的类型，用来简单的约束开发
# 分别代表：
# list   列出接收广播worker，
    # alive 简单的检查存活状态，目前只返回平台信息，后续可能会配置获取更多信息。
    # check 后续可能会改名字，因为预计是想用来实现检查各个任务执行的当前状态信息。用以统计。
# run    执行任务（包含属性设置），
# attach 接入某个任务队列，修改其日志输出模式，让其向任务端传入日志，
    # set 由于使用场景不多，替换该功能层级，作为 attach 的一个部分，
    # connect 也将包含该功能，作为其 attach 两个下数功能之一的带参数的功能部。
# 去除dump功能，因为dump功能和线上命令的相关性不大。
VREDIS_COMMAND_TYPES = ['list','run','attach','test'] 
VREDIS_COMMAND_STRUCT = {'command','subcommand','settings'}





# 开启 DEBUG 状态会让调试时 worker 监控 VREDIS_PUBLISH_SENDER 的链接状态
# 这个链接状态可作为一个开关来对 worker 本身进行一定执行控制.
DEBUG = True


# 实时回写控制台日志
# 随机选择一个任务进行实时日志回写
# 当指定 taskid 和 workerid 进行过滤输出时，“随机选择一个”的配置就会失效
# 如果这里不设置的话，就默认是全部
VREDIS_KEEP_LOG_CONSOLE = True
VREDIS_FILTER_LOG_RANDOM_ONE = True
VREDIS_FILTER_LOG_TASKID = None
VREDIS_FILTER_LOG_WORKERID = None

# 用以过滤执行的任务，默认是全部都执行任务
# 注意，执行任务和执行回写是两个不同配置，请注意。
# 并且执行任务没有 “随机选择一个” 执行的 DEBUG 选择
VREDIS_FILTER_TASKID = None
VREDIS_FILTER_WORKERID = None