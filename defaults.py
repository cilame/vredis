# type: hmap, id 自增作为 taskid
VSCRAPY_SENDER = 'vscrapy:sender'
VSCRAPY_SENDER_ID = 'id'




# 用来对爬虫状态的执行进行控制的
VSCRAPY_SENDER_START = 'vscrapy:sender:start'
VSCRAPY_SENDER_RUN   = 'vscrapy:sender:run'
VSCRAPY_SENDER_STOP  = 'vscrapy:sender:stop'
VSCRAPY_SENDER_TIMEOUT_START = 3
VSCRAPY_SENDER_TIMEOUT_RUN   = 2
VSCRAPY_SENDER_TIMEOUT_STOP  = 3



#
# 在程序执行过程中，会以 vscrapy:sender: + taskid 的字符串作为管道列表来传送任务状态
# eg. 23号任务提交后，任务执行结果会通过 redis 的列表名 vscrapy:sender:23 传回去，让 sender 知道
# 上述方法会让 redis 的存储变得非常恶心
# 考虑到这点后续将使用


# type: hmap, id 自增作为 spider
VSCRAPY_SPIDER = 'vscrapy:spider'
VSCRAPY_SPIDER_ID = 'id'


# 由于 redis 库自带的广播链接问题,需要在这里设置一个心跳包来维持广播的存活
VSCRAPY_HEARTBEAT_TIME = 60
VSCRAPY_HEARTBEAT_TASK = -1

# type: publish
VSCRAPY_PUBLISH_WORKER = 'vscrapy:publish:worker'
VSCRAPY_PUBLISH_SENDER = 'vscrapy:publish:sender'


# 开启 DEBUG 状态会让调试时 worker 监控 VSCRAPY_PUBLISH_SENDER 的链接状态
# 这个链接状态可作为一个开关来对 worker 本身进行一定执行控制.
DEBUG = True
