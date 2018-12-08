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
# run    执行任务（属性设置），
# set    动态设置属性，
# attach 接入某个任务队列，修改其日志输出模式，让其向任务端传入日志，
# dump   取数据（不在run执行中设定输出方式，默认将获取数据传入redis）
VSCRAPY_COMMAND_TYPES = ['list','run','set','attach','dump','test']
VSCRAPY_COMMAND_STRUCT = {'command','subcommand','setting'}





# 开启 DEBUG 状态会让调试时 worker 监控 VSCRAPY_PUBLISH_SENDER 的链接状态
# 这个链接状态可作为一个开关来对 worker 本身进行一定执行控制.
DEBUG = True

VSCRAPY_KEEP_REALTIME_LOG = True
VSCRAPY_KEEP_CONSOLE_LOG = True

# 如果这里不设置的话，就默认是全部
VSCRAPY_FILTER_TASKID = None
VSCRAPY_FILTER_WORKERID = None
