
##### 只需部署一个 redis ，便可轻松使用分布式。

```
一个极其方便基于 redis 的多任务分布式 python 脚本执行的函数库。
其最大的特点就是与一般脚本几乎无缝衔接（一个装饰器即可将函数分布式化）
并且支持多任务下的实时任务信息回显！！！
    # 当你提交的多个任务中有 print 函数输出，错误信息输出，都能分别回显。
    # 多任务同时执行也会根据任务 ID 进行回传信息的分发。保证多人开发时不冲突。
```

- ##### 安装方式

```bash
# 1）通过 pip 直接从pypi上下载安装
C:\Users\Administrator>pip install vredis.py
# 2）通过 pip+git 从github上下载安装
C:\Users\Administrator>pip install git+https://github.com/cilame/vredis.git
```

- ##### redis 的配置需要注意的地方

```bash
# 1）如果服务器内存比较小可能会因为快照存储问题导致异常，可以将 redis.conf 文件内部的 
#    默认参数 “stop-writes-on-bgsave-error” 这行后面的 “yes” 改为 “no”。
# 2）尽量设置一个密码保证数据库的安全。
```

- ##### 工作端连接方式

```python
# 安装该工具库后会给一个命令行工具，你可以通过命令行工具直接开启 worker
# 两种开启伺服 worker 的方式，使用哪种都可以。
# 1) 使用命令行来实现 worker 端的启动
# C:\Users\Administrator>vredis worker --host 47.99.126.229 --port 6379 --password vredis --db 0
# C:\Users\Administrator>vredis # 直接输入工具名字就是命令行工具的帮助文档

# 2) 使用脚本的方式实现 worker 端的启动
# start_worker.py
import vredis
s = vredis.Worker.from_settings(host='47.99.126.229',port=6379,password='vredis')
s.start()
```

- ##### 发送任务端的脚本编写

```python
from vredis import pipe

# 这里的 pipe 是实例，是延迟连接 redis 的开发方式。
# 只要用 pipe 这个实例 connect 就可以连接上服务器。
# 如果什么都不写，甚至不写 pipe.connect(...) 这一行，
# 那么就会默认在 “开始执行任务” 后再连接 localhost:6379 无密码，db=0.
# 不过一般来说都是需要自己主动连接一个特有的 redis 服务器。只在本机使用就不算是分布式了。



pipe.connect(host='47.99.126.229',port=6379,password='vredis')

#pipe.DEBUG = True # worker端是否进行控制台打印。我个人开发时会打开，一般没必要。
#  因为只是数据不在 worker 端打印，原本会打印的那些数据还是会回传到 redis 内。
#  一个 pipe 实例在 “开始执行任务” 后会从 redis 服务器上拿到一个唯一 taskid。
#  这样，不同的人执行脚本时 pipe 实例维护的都是不同的 taskid。这样设计多人使用才不会冲突。
#pipe.KEEPALIVE = False （实时回显的开关，默认True，关闭则变成提交任务模式）
#  实时回显的模式：
#  实时回显的模式下，如果脚本关闭，则任务 worker 端就会中断相应的 taskid 任务。
#  开发时 KEEPALIVE=True 的默认模式是最方便调试、也是最不容易浪费资源的一种方式。
#  提交模式后面会有说到。
#  提交任务模式：
#  对于一些人来说只想把任务提交上去就等待任务执行，不需要挂钩发送端是否存活，想让任务发送完就让脚本停止。
#  那么这也很简单，只需要关闭保持连接的标记即可（pipe.KEEPALIVE = False，这里的代码要在函数发送前配置），
#  这样发送端就不会回显。不过，如果函数内部有 print 函数虽然不会回显，
#  但是还是会消耗部分资源让 print 的输出和错误信息传入日志管道，
#  所以如果不想耗费这点资源，那就在 “提交式的任务” 里面尽量不要写 print 函数即可。
#  另外对于 “提交模式的任务” 可以通过 vredis 命令行工具进行停止。停止时会删除执行任务队列。
#pipe.QUICK_SEND = False（是否快速提交任务的开关，默认True）
#  默认开启，开启会以线程池的方式进行任务的提交，对 redis 的内存有一定的要求
#  因为在测试过程中出现之前都没有出现过的错误（redis内存不足）：
#  MISCONF Redis is configured to save RDB snapshots, but is currently not able 
#  to persist on disk. Commands that may modify the data set are disabled. 
#  Please check Redis logs for details about the error.
#  网上的解决办法，修改 redis.conf 文件内部的 “stop-writes-on-bgsave-error yes” 这行，将
#  配置参数改为 “stop-writes-on-bgsave-error no” 即可。
#  由于之前都没有出现过该问题，只在这次测试有这个问题。并且，
#  检查日志文件发现是内存不够的问题，总之这个任务的开启在测试中的结论是，
#  多线程提交会稍微增加 redis 内存负担，如果想要单线程提交，
#  设置 pipe 配置参数 QUICK_SEND 为 False 即可，也可以考虑增加内存。




# 接口的设计：只需要仅仅以 pipe 实例作为装饰器即可。极低的代码入侵，不加装饰器甚至几乎无障碍执行
# 被装饰的函数代码会被序列化传到每个 “发送任务时” 接收到的 worker 端上并重新构筑成函数，
# 同时接收到任务的 worker 端也会针对该次任务请求的 taskid 分配执行资源
# 装饰时只生成函数的序列化数据，等待第一次执行函数（传入任务）时会连接 worker 并获取唯一 taskid
# 然后开始传输任务。
@pipe
def some(i):
    # 不过写脚本的时候，尽量将需要引入的库写在函数内部。就这点要求。
    # 如果分布式的机器没有该库，需要通过 pip 进行下载，
    # 那么你也可以通过命令行工具 vredis cmdline 直接传输 pip 下载的命令行指令过去下载。
    # 详细可见后面的说明
    import time, random 
    time.sleep(random.randint(1,2))
    print('use func:{}, rd time:{}'.format(i,rd))
    return 123 
    # 函数 return 的数据会被简单的包装成 json 数据直接传入存储管道。
    # 默认会根据 taskid 分配一个名为 default 的的存储空间
    # 后续会根据 taskid 和空间名字进行数据抽取的工作，下面会说到



# pipe 中的 table 函数可以让被装饰的函数分配不同的存储空间，用于提取数据时使用
@pipe.table('mytable')
def some2(i):
    print('use func2:{}'.format(i))
    return 333,444
    # 如果函数不 return 数据那么就不会存储
    # 如果返回的数据是“迭代器”或者是 tuple，list 这两种类型。
    # 那么就会迭代着取出数据，然后再进行 json 的包装传入数据
    # 但是如果你有想传入一个列表数据作为一条数据，那么可以对列表数据再进行一次包装
    # 例如上面的返回是 tuple 的数据，你想要将其作为一条数据存入那么就如下再包一层即可
    # eg. 
    # return [[333,444]]



# 就按照一般的函数使用方式就可以将 函数名字，函数的参数 传入redis任务管道
# 到时候会有 接收到任务的 worker 对相应的任务进行接收并执行。
for i in range(100):
    some(i) # 被装饰的函数变成发送函数，发送到 redis 管道
    some2(i)
```

- ##### 数据的提取的脚本编写

```python
from vredis import pipe
pipe.connect(host='47.99.126.229',port=6379,password='vredis')
for i in pipe.from_table(taskid=29):
    print(i)

# 任务不结束不能抽取数据，会出直接抛出异常
# from_table 的第二个参数就可以传入 table 的名字，也就是存储的命名空间
# 默认是以 method='range' 方式提取数据，取完数据后，数据还是会占用 redis 的存储空间。
# 所以如果确定只提取这一次，不想消耗存储空间，那么可以在 from_table 里面设置 method='pop' 即可。
```

- ##### 命令行执行的方式

```bash
C:\Users\Administrator>vredis --help

# 直接输入 --help 就已经能看全部的详细文档，也不必详述。不过，这里主要想说的是
# 对于一些简单的命令行操作，可以通过 cmdline 指令连接上之后就能直接输入命令行指令让远端机器执行
# 通过连接可以得到一个非常简陋的类 bash 的指令传输区，在 cmd/ 后面直接输入指令就能传递执行
# 主要用来 pip 安装一些远端没有的库函数。目前请勿传输会中途需要卡住 bash的指令，例如任意会弹出 y/n 的指令。

PS C:\Users\Administrator\Desktop\vredis> vredis cmdline -ho xx.xx.xx.xx -po 6666 -pa vredis -db 0
[ use CTRL+PAUSE to break ]
cmd/
```

- ##### 如何检查你的任务情况

```bash
# 因为 --help 文档里面已经写的很详细了，所以这里就给一个简单的指令模板以及其执行的结果作为参考。
# vredis stat 指令必须要添加 -ta,--taskid 参数来指定需要检查的任务id。

C:\Users\Administrator>vredis stat -ho xx.xx.xx.xx -po 6666 -pa vredis -db 0 -ta 23
[ REDIS-SERVER ] host:47.99.126.229, port:6379
   taskid  collect  execute     fail     stop
   ------   ------   ------   ------   ------
      138      352       32        0     True
      139      430       40        0     True
      140      405       38        0     True
      141      374       35        0     True
      142      351       33        0     True
      143      276       27        0     True
      144      283       26        0     True
      145      259       24        0     True
      146      205       19        0     True
      147      283       26        0     True
   ------   ------   ------   ------   ------
        -  collect  execute     fail  undistr
      all     3218      300        0        0

# collect 代表收集的数量
# execute 代表执行的函数数量
# fail 代表错误函数数量（异常超过3次）
# undistr 代表还未被分发出去的任务数量
```

- ##### 配置默认参数，让命令行工具使用更方便

```bash
# 增加默认配置数据的方法，使用方法在 vredis 帮助里有描述，很简单。
# 如果什么都不写，默认打印当前配置状态 “vredis config”
# 只有以下 4 个参数需要配置。

C:\Users\Administrator>vredis config -ho xx.xx.xx.xx -pa vredis
current defaults [use -cl/--clear clear this settings]:
{
    "host": "xx.xx.xx.xx",
    "port": 6379,
    "password": "vredis",
    "db": 0
}
```

- ##### 一些优势

```
1 方便的开启，简约的脚本使用方式，以及更加友好的部署
    只需要用该库的命令行指令连接上 redis，就能为分布式脚本提供一个可执行的算力。
    装饰器接口可以让开发者自由的从本机与分布式来回切换。
    部署上不是传统的 sender -> master -> worker 模式开发，
    这里只有 sender、worker，以及一个干干净净的 redis。
    部署非常轻松，甚至随便叫一个 pythoner 下载了这个库，一行命令开启 worker端连接上 redis就能提供服务。
2 方便的 DEBUG
    极低的代码入侵，能让你像是在本地开发一样开发分布式脚本。
    而且由于实时回显的强大功能，可以让你更快更方便的 DEBUG 脚本发生的问题。
    开启实时回显时，如果脚本断开，那么该 taskid 的任务就会被 worker 端中断，
    面对一些仍在测试的中却提交了一个非常大数量的任务，也可以方便的断开重调，在不影响其他任务的情况下节约资源。
    任务如果出现异常，则会重跑。但如果重跑超过 3 次便会将任务放入错误任务收集区。保证更好的调试。
3 支持多任务，多人开发，任务安全
    支持多任务同时执行！每次脚本执行都会维护一个 taskid。让不同的任务同时执行时会根据 taskid 维护他们的配置空间。
    也就是说，你只要让别人下载该库然后用上面的示例连接上这个 redis，就能用他们的计算机作为你的分布式资源的一部分。
    并且，考虑到 worker 端可能意外断开的情况，所以设计了任务缓冲区进行对任务完整性的保护。
4 简单的日志信息
    例如你想看23号任务的执行情况你可以在安装工具后使用 "vredis stat -ta 23" 指令查看（默认查看本机redis）
    当然，你的 redis-server 配置不一样的话，就需要在命令行里面配置 redis-server 的信息。
    类似下面的指令：
    "vredis stat -ta 23 -ho xx.xx.xx.xx -po 6666 -pa vredis -db 0"
    "vredis stat -ta 23 --host xx.xx.xx.xx -port 6666 -password vredis --db 0"

只要一个 redis 服务器，你就可以让任何能连上分布式的电脑变成你分布式的一部分。
```