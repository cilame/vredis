
##### 只需部署一个 redis ，便可轻松使用分布式。

```
一个极其方便基于 redis 的多任务分布式 python 脚本执行的函数库。
其最大的特点就是与一般脚本几乎无缝衔接，并且支持实时回显。
    # 当你提交的任务中有 print 函数，错误信息都能实时回显。
    # 多任务同时执行也会根据任务 ID 进行回传信息的分发。保证多人开发时不冲突。
```

- ##### 工作端连接方式

```python
# 使用命令行来实现 worker 端的启动
# C:\Users\Administrator>vredis worker --host 47.99.126.229 --port 6379 --password vilame --db 0
# C:\Users\Administrator>vredis # 直接输入工具名字就是命令行工具的帮助文档

# 使用脚本的方式实现 worker 端的启动
# start_worker.py
import vredis
s = vredis.Worker.from_settings(host='47.99.126.229',port=6379,password='vilame')
s.start()
```

- ##### 发送任务端的脚本编写

```python
from vredis import pipe

# 这里的 pipe 是实例，是延迟连接 redis 的开发方式。
# 只要用 pipe 这个实例 connect 就可以连接上服务器。
# 如果什么都不写，甚至不写 pipe.connect(...) 这一行，
# 那么就会默认在 “开始执行任务” 后再连接 localhost:6379 无密码，db=0.
# 不过一般来说都是需要自己主动连接一个特有的 redis 服务器。



pipe.connect(host='47.99.126.229',port=6379,password='vilame')

#pipe.DEBUG = True # worker端是否进行控制台打印。我个人开发时会打开，一般没必要。
# 一个 pipe 实例在 “开始执行任务” 后会从 redis 服务器上拿到一个唯一 taskid。
# 这样，不同的人的 pipe 实例维护的都是不同的 taskid，便于多人使用。
#pipe.KEEPALIVE = False （实时回显的开关，默认True，关闭则变成提交任务模式）
# 实时回显的模式下，如果脚本关闭，则任务 worker 端就会中断相应的 taskid 任务。
# 开发时 KEEPALIVE=True 的默认模式是最方便调试、也是最不容易浪费资源的一种方式。



# 接口的设计：极低的代码入侵，不加装饰器甚至几乎无障碍执行
@pipe
def some(i):
    # 不过写脚本的时候，尽量将需要引入的库写在函数内部。就这点要求。
    # 如果分布式的机器没有该库，需要通过 pip 进行下载，
    # 那么你也可以通过命令行工具 vredis 直接传输 pip 下载的命令行指令过去下载。
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

for i in range(100):
    some(i) # 被装饰的函数变成发送函数，发送到 redis 管道
    some2(i)



# 提交任务模式：
# 对于一些人来说只想把任务提交上去就等待任务执行，不需要挂钩发送端是否存活，
# 那么这也很简单，只需要关闭保持连接的标记即可，这样发送端就不会回显，
# 但还是会消耗部分资源让 print 的输出和错误信息传入日志管道
# 所以如果不想耗费这点资源，那就在提交式的任务里面尽量不要写 print 函数即可。
```

- ##### 数据的提取的脚本编写

```python
from vredis import pipe
pipe.connect(host='47.99.126.229',port=6379,password='vilame')
for i in pipe.from_table(taskid=29):
    print(i)

# 任务不结束不能抽取数据，会出异常
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
# 主要用来 pip 安装一些远端没有的库函数。

PS C:\Users\Administrator\Desktop\vredis> vredis cmdline -ho xx.xx.xx.xx -po 6666 -pa vilame -db 0
[ use CTRL+PAUSE to break ]
cmd/
```

- ##### 一些优势

```
1 方便的开启
    只需要用该库的命令行指令连接上 redis，就能为分布式脚本提供一个可执行的算力。
2 方便的 DEBUG
    而且由于实时回显的强大功能，可以让你更快更方便的 DEBUG 脚本发生的问题。
    开启实时回显时，如果脚本断开，那么该 taskid 的任务就会被 worker 端中断，在不影响其他任务的情况下节约资源。
3 支持多任务，多人开发
    支持多任务同时执行！每次执行都会维护一个 taskid 让不同的任务同时执行时会根据 taskid 维护他们的配置空间。
    也就是说，你只要让别人下载该库然后用上面的示例连接上这个 redis，就能用他们的计算机作为你的分布式资源的一部分。
4 简单的日志信息
    接口开发完毕，暂时还需要对接命令行接口。

你可以让任何人瞬间变成你分布式的一部分。
```