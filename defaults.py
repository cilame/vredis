# type: hmap
VSCRAPY_SENDER = 'vscrapy:sender'
# type: hmap，自增作为 taskid
VSCRAPY_SENDER_ID = 'id'

#
# 在程序执行过程中，会以 vscrapy:sender: + taskid 的字符串作为管道列表来传送任务状态
# eg. 23号任务提交后，任务执行结果会通过 redis 的列表名 vscrapy:sender:23 传回去，让 sender 知道
# 上述方法会让 redis 的存储变得非常恶心
# 考虑到这点后续将使用




# 用以后续扩展对爬虫信息的管理
# 每次开始时从 1 开始请求一个 spider id 号码来方便管理
VSCRAPY_SPIDER = 'vscrapy:sender'
VSCRAPY_SPIDER_ID = 'id'



# type: publish
VSCRAPY_PUBLISH = 'vscrapy:publish'





DEBUG = True
