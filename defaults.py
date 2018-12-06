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
# 经过考虑不会使用广播形式实现 worker 配置的动态修改。
# “修改配置” 的任务也将会通过一般任务管道发送过去。
# worker 端虽然一般任务执行用的线程池，但是配置用其他线程池实现。

# 执行任务的线程数量，为防止线程过量导致问题，暂时是使用线程来实现功能。
# 后期考虑动态修改线程数量的配置实现，以前写 vthread 库的时候实现过，
# 不过这里的配置已经是非常重要的 worker 全局配置了。
VSCRAPY_WORKER_THREAD_NUM = 16
VSCRAPY_WORKER_THREAD_SETTING_NUM = 3

# 开启 DEBUG 状态会让调试时 worker 监控 VSCRAPY_PUBLISH_SENDER 的链接状态
# 这个链接状态可作为一个开关来对 worker 本身进行一定执行控制.
DEBUG = True
