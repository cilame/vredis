
##### 只需部署一个 redis ，便可轻松使用分布式。

- ##### 一个最简单的分布式

```bash
# 该分布式框架只有任务发送端和任务伺服端。
# 所以你只需要有一个正常的 redis 服务器。
# 然后使用下面的方式部署就可以使用。
# 仅依赖安装 redis 库。
# 开发于 python3.6 版本。
# 一次部署，任意任务、任意次执行，且多任务互不干扰。


【 基础配置 】：
    # 无论发送端和工作端都需要进行这两项配置
    # 安装。安装后会自动生成一个 vredis 的命令行工具，通过工具配置 redis信息。
    cmd>pip install vredis.py
    cmd>vredis config --host xx.xx.xx.xx --password xxxxx
    # 在第二步如果有更多的连接redis的配置就按照vreids的说明配置即可。
    # vredis config 命令后面不添加配置内容，则仅仅显示当前配置。


【 部署工作端 】：
    cmd>vredis worker
    # 启动任务端。（如果是linux可以在命令后加 &后台启动 “vredis worker &”）
    # 配置后启动任务端便可以让任何带有 python 平台变成你的任务机。
【 任务发送端 】：
    # 下面是一个最简单的分布式脚本 test.py
    from vredis import pipe
    @pipe
    def do_something(a,b):
        print(a+b)
    for i in range(1000):
        do_something(i,i**3) 
    # 被装饰的函数变成发送任务函数，将函数发送到待执行任务队列中，由服务机执行。
    # 执行脚本的时候会有输出一个任务taskid
    # 后续根据taskid来查询任务执行情况或者，获取任务收集到的数据。


检查任务执行的状况：
    >vredis stat --taskid xx
    # 根据任务id查看任务执行情况
```

- ##### 安装方式

```bash
# 1）通过 pip 直接从pypi上下载安装（pip直接下载的名字后面有.py，请注意别下载错了。）
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
# 如果什么都不写，甚至不写下面的 pipe.connect(...) 这一行，那么就会从配置里面去取数据
# vredis 会在 “开始执行任务” 后再连接 localhost:6379 无密码，db=0.（这是初始化配置）
# 不过如果在 HOME 工作目录下创建一个 .vredis 的配置文件，那么就会这个配置文件里面读默认配置
# 这里面的配置可以通过命令行工具修改，这样的话，真的就只需要一行代码就能实现脚本化的分布式代码了。
# 只要你下载了该库，配置了 redis 和工作段，配置了本地 vredis 的 config 。
# 那么你就能直接连 pipe.connect(...) 这个函数都不需要，一个装饰器就能实现分布式。
# 不过如果有需要的话 connect 配置会优先于默认配置。默认配置会优先于初始化配置。



pipe.connect(host='47.99.126.229',port=6379,password='vredis')

#pipe.DEBUG = True # worker端是否进行控制台打印。我个人开发时会打开，一般没必要。
#  因为只是数据不在 worker 端打印，原本会打印的那些数据还是会回传到 redis 内。
#  一个 pipe 实例在 “开始执行任务” 后会从 redis 服务器上拿到一个唯一 taskid。
#  这样，不同的人执行脚本时 pipe 实例维护的都是不同的 taskid。这样设计多人使用才不会冲突。
#pipe.KEEPALIVE = False （实时回显的开关，默认True，关闭则变成提交任务模式）
#  实时回显的模式：
#  实时回显的模式下，如果脚本关闭，则任务 worker 端就会中断相应的 taskid 任务。
#  开发时 KEEPALIVE=True 的默认模式是最方便调试、也是最不容易浪费资源的一种方式。
#  提交任务模式：
#  对于一些人来说只想把任务提交上去就等待任务执行，不需要挂钩发送端是否存活，想让任务发送完就让脚本停止。
#  那么这也很简单，只需要关闭保持连接的标记即可（pipe.KEEPALIVE = False，这里的代码要在函数发送前配置），
#  这样发送端就不会回显。并且也不会占用回传管道的资源，造成浪费。
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
#  设置 pipe 配置参数 QUICK_SEND 为 False 即可，最简单方式就是升级服务器配置，增加内存。
#pipe.DUMPING = True（默认为False）
#  该设置 DUMPING 只能在 KEEPALIVE 为真时候（实时模式）才能打开，否则报错
#  主要的功能就是在实时抓取的状态下，直接将数据收集到本地的文件中，不存储进 redis，便于少量数据收集。
#  打开后执行脚本，会在脚本执行的路径下生成一个以精确到秒的日期文件名字的json 文件。




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

- ##### 数据的提取

```bash
# 推荐使用命令行提取数据，获取默认传入redis的数据必须配置taskid
# limit是数量显示，从后往前获取搜集到的数据的数量限制
# 如果不设置 --file 则默认控制台输出，如果设置则写入文件
# --file 绝对路径和相对路径。
# 输出的文件格式类似于 scrapy 框架的默认写文件的
cmd>vredis dump --taskid 19 --limit 10
cmd>vredis dump --taskid 19 --limit 10 --file 123.txt


# 使用脚本的方式提取数据
from vredis import pipe
# pipe.connect(host='47.99.126.229',port=6379,password='vredis')
# 是否pipe.connect(...)取决于你是否通过 vredis 工具配置了redis连接的配置
for i in pipe.from_table(taskid=19):
    print(i)
# 任务不结束不能抽取数据，会出直接抛出异常
# from_table 的第二个参数就可以传入 table 的名字，也就是存储的命名空间
# 默认是以 method='range' 方式提取数据，取完数据后，数据还是会占用 redis 的存储空间。
# 所以如果确定只提取这一次，不想消耗存储空间，那么可以在 from_table 里面设置 method='pop' 即可。
```

- ##### 命令行执行的方式

```bash
PS C:\Users\Administrator\Desktop\vredis> vredis cmdline
[ use CTRL+PAUSE(win)/ALT+PAUSE(linux) to break ]
cmd/

# 在该cmdline的情况下传输命令行。
# 测试中，在window上能够通过pip进行对库的安装，但是在linux上暂时不行。
# 同时，在该处有两个特别的命令 ls/list
# 这两个命令被覆盖为“输出每个工作段的机器型号”。
```

- ##### 如何检查你的任务情况

```bash
# 因为 --help 文档里面已经写的很详细了，所以这里就给一个简单的指令模板以及其执行的结果作为参考。
# vredis stat 指令必须要添加 -ta,--taskid 参数来指定需要检查的任务id。
# 其他的配置在默认配置里面有的话就可以不用写，如果没有，可以直接在命令行中添加。

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
# 增加默认配置参数的方法，使用方法在 vredis 帮助里有描述，很简单。
# 如果什么都不写，默认打印当前配置状态 “vredis config”，如果有参数则进行配置。
# 只有以下 4 个参数需要配置。

C:\Users\Administrator>vredis config -ho xx.xx.xx.xx -pa vredis
current defaults [use -cl/--clear clear this settings]:
{
    "host": "xx.xx.xx.xx",
    "port": 6379,
    "password": "vredis",
    "db": 0
}

# 命令行只要是需要这四个参数的，配置了默认参数，那么就会从默认参数去取配置。命令行工具更好用了。
# 另外配置的优先级是：命令行配置 > 默认配置 > 初始化配置（localhost:6379 无密码，db=0）。
```

- ##### 一些优势

```
1 方便的开启，简约的脚本使用方式，以及更加友好的部署
    一次部署，任意任务、任意次执行，且多任务互不干扰
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
    例如你想看23号任务的执行情况你可以在安装工具后使用 "vredis stat -ta 23" 指令查看（通过默认redis配置查看）
    想查看最新的任务情况使用 "vredis stat -la"
    想查看最新的N个任务的简要状态 "vredis stat -ls"

因为有任务安全、部署简单这两点，所有有一个最大的优势：
    只需一个redis服务器，你可以以最快的速度搜集闲散资源来实现你的分布式。
    手机上如果有装termux一类的类linux系统的工具app，你甚至可以用手机作为你的分布式工作端！
```
