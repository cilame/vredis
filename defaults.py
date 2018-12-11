# type: hmap, id 自增作为 taskid
VSCRAPY_SENDER = 'vscrapy:sender'
VSCRAPY_SENDER_ID = 'id'

# 用来对爬虫状态的执行进行控制的
VSCRAPY_SENDER_START = 'vscrapy:sender:start'
VSCRAPY_SENDER_RUN   = 'vscrapy:sender:run'
VSCRAPY_SENDER_STOP  = 'vscrapy:sender:stop'
VSCRAPY_SENDER_TIMEOUT_START = 3
VSCRAPY_SENDER_TIMEOUT_RUN   = 1
VSCRAPY_SENDER_TIMEOUT_STOP  = 3

# 处理在 sender 端同步log时出现断连接的 worker 超时处理次数
VSCRAPY_OVER_BREAK = 2

# type: hmap, id 自增作为 workerid
VSCRAPY_WORKER = 'vscrapy:worker'
VSCRAPY_WORKER_ID = 'id'
# 后续在程序中增加 VSCRAPY_WORKER + 'taskid' 作为一个自增的数字key，
# 用以实现随机抽取一个进行回写的动作选择

# type: publish
VSCRAPY_PUBLISH_WORKER = 'vscrapy:publish:worker'
VSCRAPY_PUBLISH_SENDER = 'vscrapy:publish:sender'

# “修改配置” 的任务将会在非任务线程中实现。
# 执行任务的线程数量，为防止线程过量导致问题，暂时是使用线程来实现功能。
# 不过这里的配置已经是非常重要的 worker 全局配置了。
VSCRAPY_WORKER_THREAD_NUM = 16
VSCRAPY_WORKER_THREAD_SETTING_NUM = 3

# 命令的类型，用来简单的约束开发
# 分别代表：
# list   列出接收广播worker，
    # alive 简单的检查存活状态，目前只返回平台信息，后续可能会配置获取更多信息。
    # check 后续可能会改名字，因为预计是想用来实现检查各个任务执行的当前状态信息。用以统计。
# run    执行任务（包含属性设置），
# attach 接入某个任务队列，修改其日志输出模式，让其向任务端传入日志，
    # set 由于使用场景不多，替换该功能层级，作为 attach 的一个部分，
    # connect 也将包含该功能，作为其 attach 两个下数功能之一的带参数的功能部。
# dump   取数据（不在run执行中设定输出方式，默认将获取数据传入redis）
VSCRAPY_COMMAND_TYPES = ['list','run','attach','dump','test']
VSCRAPY_COMMAND_STRUCT = {'command','subcommand','settings'}





# 开启 DEBUG 状态会让调试时 worker 监控 VSCRAPY_PUBLISH_SENDER 的链接状态
# 这个链接状态可作为一个开关来对 worker 本身进行一定执行控制.
DEBUG = True

# 实时回写控制台日志
VSCRAPY_KEEP_REALTIME_LOG = True
VSCRAPY_KEEP_CONSOLE_LOG = True

# 随机选择一个任务进行实时日志回写
VSCRAPY_FILTER_RANDOM_ONE = True
# 当指定 taskid 和 workerid 进行过滤输出时，“随机选择一个”的配置就会失效
VSCRAPY_FILTER_TASKID = None
VSCRAPY_FILTER_WORKERID = None
# 如果这里不设置的话，就默认是全部
