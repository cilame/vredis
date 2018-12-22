
##### 只需部署一个 redis ，便可轻松使用分布式。

```
只需要用该库的 worker 端连接上 redis，就能为分布式脚本提供一个可执行的算力
sender 端所有的函数执行都将以管道的方式传递到 redis， worker 端会从管道抽出来执行。
支持多任务同时执行！每次执行都会维护一个 taskid 让不同的任务同时执行时会根据 taskid 维护他们的配置空间。
    # 也就是说，你只要让别人下载该库然后用下面示例的工作端连接方式连接上这个redis，就能用他们的计算机作为你的分布式爬虫的一部分。
    # （目前，基本的函数空间配置以及函数执行已经实现，不过，请求类的库如 requests 怎么更好的传递这边尚在考虑。）
    # 接口暂时如下，后续改变的话会将改变的内容写进去的。
```

- ##### 工作端

```bash
C:\Users\Administrator>vredis worker -ho 47.99.126.229 -po 6379 -pa vilame -db 0
# 使用命令行来实现 worker 端的启动

C:\Users\Administrator>vredis
# 帮助文档，里面介绍更多详细配置和使用方法
```

```python
import vredis
s = vredis.Worker.from_settings(host='47.99.126.229',port=6379,password='vilame')
s.start()
# 使用脚本的方式实现 worker 端的启动
```

- ##### 发送任务端

```python
from vredis import pipe

pipe.connect(host='47.99.126.229',port=6379,password='vilame')
pipe.DEBUG = True # worker端是否进行控制台打印。

# 极低的代码入侵，不加装饰器甚至完全无障碍执行
@pipe
def some(i):
    import time, random
    rd = random.randint(1,2)
    time.sleep(rd)
    print('use func:{}, rd time:{}'.format(i,rd))

@pipe
def some2(i):
    print('use func2:{}'.format(i))

for i in range(100):
    some(i) # 被装饰的函数变成发送函数，发送到 redis 管道
    some2(i)
```


##### 以下是从最初考虑使用 scrapy 的想法变异到现在放弃 scrapy 通过目前脚本传递的方式
##### 先去实现共享的分布式脚本任务执行的思路过程，包含一些目前需要解决的问题，后续还在增加。

```
# 为了有别于工作中所使用的分布式脚本
# 想尝试开发一个个人使用的更加便于开发者使用的分布式代码
# 希望能够从 “对开发者更加友好” 的角度开始从零开始开发一个自己的分布式的爬虫
# 基于 scrapy 以及 redis 并且将有别于工作中使用特殊脚本传递形式来实现的方法进行区分
# 最主要的目的就是让开发者能像是在本机调试一样去调试分布式
# 仅仅像是开发单机的 scrapy 爬虫脚本一样非常快就能直接使用线上的开源分布式架构

# 首先，创建这个库的目标是希望将 scrapy crawl 本地爬虫与分布式爬虫进行接口统一
# 让本地爬虫开启的代码，只需修改一个字母即可实现分布式爬取
# 一般本机 scrapy：
    # 使用本机 scrapy 爬虫
    scrapy crawl spidertest

# 目标分布式爬虫接口实现：
    # 使用分布式 scrapy 爬虫
    vscrapy crawl spidertest
    # 检查所有爬虫状态，分布式特有的一些功能
    vscrapy -l
    # 连接这些任务的实时输出状态
    vscrapy -c --connect 123,333,345 
    # 其他功能想到就添加进去
    ...

并且在部署上做到尽可能的简单。
部署和实现一体化。

# 需求预装环境
# scrapy # 基础包目前的开发暂时没有需要
redis # 基于 redis 进行数据传输，所以肯定需要 redis，各种数据配置也需要在这里实现
# 开发过程中可能会参照部分 scrapy-redis 的细节进行优化补充

# 最重要去实现的两点
# 1 debug 要更加方便，
    [1]特别是能够传输远端爬虫队列里面的错误日志。（ DEBUG 开启状态）
    [2]发送任务端以任意方式断链执行就停止。（相同的任务才会停止）
        即，不同的发送端口每次发送时的任务id肯定不一样，一个发送端绑定一个任务 id
        该发送端任意方式断开连接则该任务 id 执行结束，不影响其他任务 id
# 2 一次部署后续将无需更新。

@20181128
先考虑信号安全传递的方法:
    现在先考虑实现信号的注册，维持和丢失的情况。 
    # 因为想要在 debug 的状态中实现，如果断开调度器时，任务自动停止。便于调试。
    # 后续需要通过类地址来获取类里面的方法字符串
    # 暂时考虑通过 class 来获取 class代码 的方式可以参考 inspect 里面的 getsource 方法。

@20181129
原本是有 master worker sender 来代表主控部，工作部，任务发送部
现在去除 master 这个主控，让部署实现变得更加简单一些。让工作端只需要知道 redis 的地址和密码即可。

@20181130
后面是考虑到如果需要全局爬虫更好的调度控制可能就需要 master 。但是感觉暂时没有特别的需要。
所以目前考虑的是实现 sender 和 worker 的调配就好了。 master 端可以延后再实现。
    # 今天的难点主要是发生在怎么处理爬虫状态上面
    # 是否开启 debug 状态也是很需要考虑的
    # 保持连接的状态来接收 log。

    # 1，考虑处理状态（开启、执行、关闭）转移的时机，考虑存储状态的结构。
    # 2，考虑怎么在正常状态处理中实现保持连接以及断开连接的信号发送。

@20181203
以上功能基本已经实现简单的雏形，不过维护任务广播的心跳功能可能会稍微有点不太合理
因为维护只需要一个信号就行，但是这里的实现是去中心处理的只有 worker 端的处理
所以目前在运行量比较少的情况下，暂时就使用每个 worker 60秒心跳广播一次来维护广播存活
    # 今天的难点可能就主要是了解一些 twisted 的框架，看看怎么处理会更好的结合
    # 目前用的是开启线程的方式来将新到的任务丢入线程去执行的（但执行端用线程可能效率低）
    # 考虑到后续 scrapy 爬虫功能的扩展，这里还需要对 scrapy 的执行要去了解。
    # 最后再根据需求将日志的格式整理得更好一些

@20181204
发现之前需要心跳的处理有误，原因是这边的一个设定失误才会超时停止，现在已经去除心跳线程
代码比之前更简洁了一些，现在需要将这边的接口弄得更像接口一点，还有虫子本身的日志处理
    # 日志处理可以考虑根据 workerid 来存放在结构里面。日志检查的接口也要并行开发处理，便于检查。
    # 目前就需要整理一下接口的处理，让函数实现更方便一些，twisted 的学习可能需要放在后面一些时间
    # 两个大问题
    # 1 如何记录日志
    # 2 如何执行任务
    # 功能角度上要先实现查询所有存活 worker 的功能
    # 通过挂钩标准输出的函数可以实现 worker 所有输出都传递到这边
    # 增加更多通过 sender 进行动态配置参数的接口

@20181205
可能需要在输出的时候再加上一层 taskid 的封装，今天考虑将日志回显标准化。
由于挂钩点唯一性 stdout 和 stderr。不方便针对任务进行挂钩。怎么增加一个选择的标识呢？
目前的想法就是通过 inspect.stack 来实现查找当前 taskid 来通过 taskid 进行传递
    # 目前已通过 inspect.stack 实现该功能
    # 不过就是传递方面可能还需要将之前的耦合性比较强的代码再整理一下
    # 后续将完整实现，能够根据 taskid 和 workerid 来监听某个任务下-
    # 某个 worker 的实时输出状态。并且后续还需扩展日志持久化处理。
    # 也就是说传一个函数脚本过去，worker 执行时不管你在里面用什么输出，都可以捕捉
    # 或是 print 或是 logging 的内容都可以回传到发送端。能捕捉的问题解决基本就OK
    # 剩下就是实现简单回传功能
    # （需要考虑根据开关实现，可能需要抽象一个 Flag 类来存放）
    # （可能挂钩函数还需要更多地与 Flag 类相关，还需要更多魔改）
    # 目前检擦实时连接状态还没有被更好的解耦。可能需要魔改迭代器？
    # 还是说因为传过去的脚本本身就是字符串，可以用正则进行插入字符串再解析？
    # 1，完善实时回传功能
    # 2，完善 Flag 类作为开关的功能
    # 3，考虑实时检测 sender 连接状态的解耦
    #     期望是在 DEBUG 状态下 sender 端断开就任务就停止，避免资源浪费

#20181206
将对应于之前的 Flag 类的想法，这边将那个想法改名为 Valve（阀门）。
将会生成一个全局的阀门实例，让所有通过阀门的任务都需要在传送过来的配置下来进行传输的控制。
eg。 在传输端将一个 DEBUG 配置传输过来，这边会根据配置将使用 DEBUG 模式来实现管道的传输。
    能够在后续指定需要哪个任务需要回传，需要哪些更多配置的操作，这样就会方便很多。
    # DEBUG：后续增加一个 workerid 查重的功能，因为可能有人指定 workerid 后续若重复存在会有问题。
    # 检查状态需要考虑
    # 后面可能需要试试考虑学一点py解释器的内容，目的是想挂钩全局的迭代工作。（或许不太可能实现）
    # 现在主要的任务：
    # 实现简单的 task 配置隔离和简单的回传显示
    # 由于想要实现这些又可能会与传送任务的指令结构有相关性，所以设计指令规范迫在眉睫。

#20181207
先考虑规范化回传的内容，确认回传的一些默认配置，先使用 logging 库覆盖现在不是很规范的 print
然后发现 logging 有很多坑，就先将就现在的状况就好，print 其实也挺好用的。
    # 简单的回写已经做好，不过，每一个都需要回写，传入管道之后这边通过过滤前缀的方式来拿出一个 worker 的回写 print
    # 不过暂时是没有支持动态的修改目标机器的 DEBUG 状态来关闭回写，这边需要考虑这类的配置，不过在功能上可能会
    # 不能挂钩比较复杂的 console 输出处理稍微有点可惜，后续有必要再考虑。print 已经非常够用了。
    # 有四个任务功能需要实现。
    # 0 检查任务
    # 1 配置任务。
    # 2 获取数据任务。（用redis就是看中这分布式共享管道功能）
    # 3 分发任务。（这里需要非常小心的考虑怎么处理脚本的传输）
    #     一般需要执行复杂任务的，这里需要添加命令行执行任务的操作
    
#20181208
作为传输的结构，暂时先考虑使用 {'command': <str> ,'subcommand': <dict> ,'settings': <dict> }
暂时都使用 print 回传的方式来进行数据回传，可以在阀门这个类上下功夫应该就能解决，不过
今天杭州下雪，太TM冷了，今天后面的时间都休息，明天再搞。
    # 吃完饭满血复活，晚上继续搞起。
    # 后续可能需要考虑在执行之前进行 worker 端口的存活验证，主要是如果在配置随机选一个端进行会写检查的话
    # 需要在发送任务之前事先知道那些任务端还活着。后续如果需要配置使用哪一个 worker 端的话，
    # 也需要事先知道那些任务端还活着。考虑通过一个隐藏任务，即不消费任务号码的任务进行特殊处理。

#20181209
现在突然发现一个很好的解决默认配置传输的方式，就是在对指令结构预检查的时候进行补充和配置，
这个很好解决了不同的指令存在相互交叉的默认配置，这样也能更好的调配工作。我觉得OK。
    # 任务的模型也越来越符合我心目中的标准了。不过还是对后期可能需要并入 twisted 表示有一定的担心
    # 因为目前是完全基于 threading 线程库进行的开发，所以后期要是改 twisted 可能需要很长时间。
    # 毕竟 twisted 的文档有点让人难受的。
    # 不过事实上目前的功能也可以在一定程度上分成一个单独的功能库出去。改成接口的形式来实现？

#20181210
今天已经明确了剩下需要开发的命令结构，暂时还不考虑其他命令的开发。以目前的任务框架进行开发先。
后续还是绕不开怎么对配置执行脚本的处理方式的开发。

#20181210
修改了部分命令的结构，宏命令更少了。整理了一下不同命令需要的默认值的处理。
之前是放在命令执行这一步时候进行默认配置，后来发现这个想法很菜，在命令生成的时候就应该进行默认值的约束了。
后续的各种命令格式化规范的异常也放在那里，这样的处理也才是比较合理的。
    # 终于还是到了要考虑脚本的执行方式的时候了。
    # 难点主要是在我想环境的传递也想要结合在里面。不然就不能实现一次部署随便运行。难受。
    # 是时候闭关修炼一波 python 的奇技淫巧了？
    #（一种习惯于先在脑子里面实现功能，到时候再在 python 里面查有没有相关的实现方法的头脑运作习惯开始了。）


#20181212
最近发现在 scrapy 在处理一些表单提交的时候出现问题，并且完全相同的配置情况下，竟然是 requests 胜出
一方面我觉得 scrapy 的依赖太强，并且要使用 twisted ，又是一堆的依赖，并且 reactor 模式开发成本较高
scrapy 的代码耦合性也很强，不如 requests 这样的更为良好的接口使用方式。
所以这边考虑将本控制传输作为一个单独的模块来开发，后续或许再想想办法以 scrapy-redis 来实现兼容 scrapy。
但是现在更倾向于 requests 库了。
    # 唐突改名，为了更好的扩展性现改名为 vredis（原名为 vscrapy）

#20181213
去除 dump 指令，因为其与线上任务的相关性不大。数据处理的方式尽量考虑通过 redis 管道来实现。
也可以考虑在脚本里面直接写入某个数据库的写入，但是这样或许太过直接了一点。

#20181217
增加 script 的指令，该指令用于脚本执行的场景，即，不会作为直接用于后续命令行开发使用的指令。
以之前写过的 vthread 线程库的思路来实现该场景下的功能。增加了 __init__.py 说明准备模块化处理了。
并且考虑到脚本处理的问题，后续需要考虑是否保持链接的处理，这里的功能很绕。就是很绕。
    # 也许主攻脚本化，去除命令行的处理可能会更好？命令行就单独用来作为 worker 端链接 redis？
    # 功能上基本完成，不过发现一个 BUG ，暂时还没想到应对这个 BUG 的处理方法。

#20181218
处理完脚本化的功能，至此，基本的功能已经能够运行起来实现。不过还有挺多小细节的功能还并未完善。
暂时还没有弄成提交模式。即提交任务后本地的脚本即停止，并且不往回显管道里面传入回显内容。
另外提交模式也要对应着 “连接模式”，即这边命令行对某个 taskid 进行 “连接”后，任务将开始回写。本地开始接收。
同时也要处理一部分 error 的存储，以及状态存储的方式。总之就是各种各样。
    # 未完善的功能：
    # 1 本地的管道要同远端的管道能够无缝衔接，则可能会该部分的解析和传递的结构
    # 2 状态检查的问题还是没有完全开始处理，可能需要一个根据 taskid 来处理的状态空间
    # 3 提交模式 以及 中途连接模式 需要考虑怎么处理各式各样代码上的开关。
    # 4 现在的任务执行队列默认是以 taskid 最大则最先执行的方式，后续需要改进。

#20181219
今天用随机获取的方式去获取任务队列，并且暂时没办法清理缓存中的内容。
目前的状况是，worker端无法抵御网络中断的问题。且在执行中发现两个网络中断存在的断点。
要是简单的使用暴力解决，代码可能会变得不优雅，很头疼。
    # 修改了部分的 sender 端监听停止的代码，让 sender 端的执行过程变得更加合理一些。

#20181220
昨天终于发现之所以挂钩 pipeline 函数的 stop 状态没用是因为那个结束并不能正常的结束，所以就会照成问题。
现在的处理方式应该是可以解决之前遗留下来的任务扫尾的工作。
    # 现在需要处理的功能
    # 1 状态记录的结构和方式
    # 2 提交模式以及中途链接的模式暂时还有点远

#20181221
解决一些细枝末节的 BUG ，今天希望能够在后面解决一些命令行处理，以及后续要处理远端命令行执行的同步功能
    # 最近需要解决的问题：
    # 1 仍然是状态几率的结构和方式
    # 2 命令行的一般实现方式现在需要开始实现了，调试起来会稍微有点麻烦。
    # 3 提交模式和中途链接模式牵涉比较复杂的开关，后需考虑。 

#20181222
以目前的状况来看发现 cmdline 这种方式与任务进行沟通的话，发现执行时的效果比想象中要好很多。
并且以这样的方式进行开发的话，subcommand 这个参数就没有存在的意义了。不过考虑后续有可能会有拓展开发，暂时不改（懒？）
用 cmdline 进行沟通的方式有一个比较好的优点就是用实例化对象维护的 taskid 会保留在内部。taskid 可以复用。
    # 现在的任务
    # 1 考虑记录结构的方式和数据，另外还要有不同表输出的拓展
    # 2 另外就剩下对命令行参数还有使用方式的一些拓展了。
    #    现在考虑的是想要在 cmdline 里面添加一些自己的语法进行一些简单的过滤，查信息，等等
    #    也就是将之前的那些命令行功能都装在 cmdline 里面。
    #    抛弃之前的提交任务命令的开发，但是保留连接回显的功能（放在cmdline里面）。
    #    因为后续将考虑脚本提交任务时，不 hook sender的存活状态。
    #    因为回显很浪费资源。
    #    另外的另外就是要考虑怎么处理，任务执行状况的记录，类似： “start”，“running”，“stop”。
    #    目前这个类似去中心化的队列怎么才能知道任务已经结束。很难啊喂。特别数出现异常的情况怎么处理。哎~
```