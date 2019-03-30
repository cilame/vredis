import sys
import argparse
import re
import time
import os
import json

from . import defaults
from .__init__ import __version__, _Table
from .worker import Worker
from .sender import Sender
from .error import PathNotExists,TaskUnstopError

vredis_command_types = ['cmdline', 'worker','stat','stop','config','dump','version']

defaults_conf = dict(
    host='localhost',
    port=6379,
    password=None,
    db=0,
)

_o_conf = dict(
    host='localhost',
    port=6379,
    password=None,
    db=0,
)

try:
    home = os.environ.get('HOME')
    home = home if home else os.environ.get('HOMEDRIVE') + os.environ.get('HOMEPATH')
    config = os.path.join(home,'.vredis')
    if not os.path.exists(config):
        with open(config,'w',encoding='utf-8') as f:
            f.write(json.dumps(defaults_conf,indent=4))
    else:
        with open(config,encoding='utf-8') as f:
            defaults_conf = json.load(f)
except:
    print('unlocal homepath.')
    pass

def init_default(args):
    global defaults_conf
    defaults_conf['host']    = defaults_conf.get('host')      if args.host == None else args.host
    defaults_conf['port']    = defaults_conf.get('port')      if args.port == None else int(args.port)
    defaults_conf['password']= defaults_conf.get('password')  if args.password == None else args.password
    defaults_conf['db']      = defaults_conf.get('db')        if args.db == None else int(args.db)
    # 优先本地配置，其次是config配置，最后才是默认配置

description = '''
usage
  vredis <command> [options] [args]

command
  worker    start a worker.
  cmdline   use cmdline connect host. and sent simple bash command.
  stat      use taskid check task work stat.
  stop      use taskid stop a task.
  dump      use taskid dump data that the task is finish.
  config    config default host,port,password,db
  version   check vredis version
{}
options
  type<param>
  -ho,--host            ::redis host.           default: localhost
  -po,--port            ::redis port.           default: 6379
  -pa,--password        ::redis password.       default: None       (means no password)
  -db,--db              ::redis db.             default: 0
  -wf,--workerfilter    ::worker filter         default: all        (cmdline)
  -ta,--taskid          ::check task work stat  default: None       (stat)
  -li,--limit           ::dump data limit       default: -1 (all)   (dump,stat)
  -nt,--nthread         ::thread number.        default: 32         (worker)
  -er,--error           ::check error info by taskid.               (stat)
  -sp,--space           ::dump data space       default: 'default'  (dump)
  -fi,--file            ::dump data filename                        (dump)
  type<toggle>
  -la,--latest          ::check for the latest task                 (stat)
  -ls,--list            ::list for check latest N task simple stat. (stat)
  -fo,--force           ::force dump data when the task incomplete. (dump)
  -cl,--clear           ::clear config, use initial configuration.  (config)

[cmd info.]
  "vredis"              ::show default info
  "vredis stat"         ::show stat info
  "vredis stop"         ::show stop info
  "vredis dump"         ::show dump info
  "vredis -h"           ::show all info
  "vredis --help"       ::show all info
'''

cmdline_description = '''
  cmdline               ::[eg.] "vredis cmdline -wf 3,6,9"
    -wf,--workerfilter  ||this parameter can only work in cmdline mode.
                        ||use "cmdline" you can enter a cmd/ mode,
                        ||you can send simple cmd command to execute.
                        ::cmd/ pip install requests
                        ||easy for such as "pip install ..." command.
                        ::cmd/ ls
                        ||if you only wanna check how many worker start
                        ||just in cmd/ mode, enter "ls" or "list" command.
'''

stat_description = '''
  stat                  ::[eg.] "vredis stat -ta 26"
    -ta,--taskid        ||this parameter can work in stat mode
    -la,--latest        ::[eg.] "vredis stat -la"
                        ||don't use taskid to check for the latest task
                        ||this parameter can only work in stat
    -ls,--list          ::[eg.] "vredis stat -ls"
                        ||list check cannot coexist with single task check
                        ||this parameter can work in stat
    -er,--error         ::[eg.] "vredis stat -er 26"
                        ||check error info by taskid.
                        ||this parameter can work in stat
'''

stop_description = '''
  stop                  ::[eg.] "vredis stop -ta 26"
    -ta,--taskid        ||this parameter can work in stop mode
'''

dump_description = '''
  dump                  ::[eg.] "vredis dump -ta 26"
    -li,--limit         ::dump data limit       default: -1 (means all)
                        ||this parameter can only work in (dump,stat) mode.
                        ||when -fi not set, this parameter will reset 10. for easy show data.
    -sp,--space         ::dump data space       default: 'default'
                        ||this parameter can only work in dump mode.
                        ||if not set, use default store space.
                        ||usually, you don't have to change the name here.
    -fi,--file          ::dump toggle
                        ||this parameter can only work in dump mode.
                        ||if set, try dump data in a local file
                        ||if not set, just get data and show it in console.
    -fo,--force         ::force dump toggle
                        ||force dump data when the task incomplete.
'''

worker_description = '''
  worker                ::[eg.] "vredis worker --host 192.168.0.77 --port 6666 --password vredis"
                        ||open a worker waiting task
                        ||all parameters of this command depend on default parameters
                        ::[eg.] "vredis worker"  (simple commond: use vredis_config)
                        ||if use simpler commond and vredis_config not set.
                        ||worker will use defaults parameters connect redis server
                        ||worker use host       localhost
                        ||worker use port       6379
                        ||worker use password   None (python type:means no password)
                        ||worker use db         0
    -nt,--nthread       ::[eg.] "vredis worker -nt 64"
                        ||thread number.        default: 32
                        ||this parameter can only work in worker mode.
'''

config_description = '''
  config                ::[eg.] "vredis config -ho xx.xx.xx.xx -po 6666 -pa vredis -db 1"
                        ||over write default config
                        ||it works in script and cmdtool.
                        ||cmd_config > vredis_config > init_config
                        ||cmd_config:       in cmdline
                        ||vredis_config:    over write defaults
                        ||init_config:      localhost:6379 password:None db:0
    -cl,--clear         ::[eg.] "vredis config -cl"
                        ||clear config
                        ||this parameter can only work in config mode.
                        ||use init_config as defaults config
                        ||init_config:      localhost:6379 password:None db:0
'''


h_description = re.sub('\{\}','',description).strip()
help_description = description.format(''.join([cmdline_description,
                                               stat_description,
                                               stop_description,
                                               dump_description,
                                               worker_description,
                                               config_description])).strip()



def _print_help(argv):
    if len(argv) == 1:
        print(h_description)
        sys.exit(0)
    if len(argv) == 2 and \
           argv[1] in ['-h','--help']:
        if argv[1] == '-h':     print(help_description)
        if argv[1] == '--help': print(help_description)
        sys.exit(0)


def deal_with_worker(args):
    print('[ use CTRL+PAUSE(win)/ALT+PAUSE(linux) to break ]')
    host    = defaults_conf.get('host')
    port    = defaults_conf.get('port')
    password= defaults_conf.get('password')
    db      = defaults_conf.get('db')
    nthread = int(args.nthread)
    print('[ REDIS ] host:{}, port:{}'.format(host,port))
    wk      = Worker.from_settings(host=host,port=port,password=password,db=db,VREDIS_WORKER_THREAD_RUN_NUM=nthread)
    wk.start()


def deal_with_stop(args):
    host    = defaults_conf.get('host')
    port    = defaults_conf.get('port')
    password= defaults_conf.get('password')
    db      = defaults_conf.get('db')
    if args.taskid is None:
        print(stop_description)
        print('pls set param:taskid for stop task.')
        print('[eg.] "vredis stop -ta 23"')
        return
    taskid  = int(args.taskid)
    _rname  = '{}:{}'.format(defaults.VREDIS_TASK, taskid)
    print('[ REDIS ] host:{}, port:{}'.format(host,port))
    sd      = Sender.from_settings(host=host,port=port,password=password,db=db)
    sd.rds.hset(defaults.VREDIS_WORKER, '{}@inter'.format(taskid), 0)
    sd.rds.ltrim(_rname,0,0)
    print('task {} ready to stop.'.format(taskid))


def deal_with_dump(args):
    host    = defaults_conf.get('host')
    port    = defaults_conf.get('port')
    password= defaults_conf.get('password')
    db      = defaults_conf.get('db')
    limit   = int(args.limit) # -1 all
    space   = args.space # None
    file    = args.file # None
    force   = int(args.force)
    if args.taskid is None:
        print(dump_description)
        print('pls set param:taskid for dump task.')
        print('[eg.] "vredis dump -ta 23 -li 100 -fi some.json"')
        return
    taskid  = int(args.taskid)
    print('[ REDIS ] host:{}, port:{}'.format(host,port))
    sd      = Sender.from_settings(host=host,port=port,password=password,db=db)

    def _dump(space,file):
        print('[ TABLE ] tablespace:{}.  collect number:{}.'.format(
            tablespace.rsplit(':',1)[1],sd.rds.llen(tablespace)))
        path,name = os.path.split(file)
        path      = path if path.strip() else os.getcwd()
        if not os.path.exists(path):
            raise PathNotExists(path)
        filepath  = os.path.join(path,name)
        try:
            TABLE = iter(_Table(sd, taskid, space, 'range', ignore_stop=bool(force), limit=limit))
            logidx = [next(TABLE)]
            pre = json.dumps(logidx[0])
        except TaskUnstopError:
            print('[ WARNING! ] task {} All stop labels did not stop completely'.format(taskid))
            print('[ WARNING! ] if you confirm that you want dump data, pls add -fo,--force')
            print('[ WARNING! ][eg.] "vredis dump -ta 23 -fi filename -fo"')
            return
        with open(filepath,'a',encoding='utf-8') as f:
            f.write('[\n')
            idx = 1
            while True:
                try:
                    data = next(TABLE)
                    if pre is not None: 
                        f.write(pre+',\n')
                    idx += 1
                    if idx%5000==0 and idx!=0:
                        print('all dump number:{}.'.format(idx))
                        logidx.append(idx)
                    pre = json.dumps(data)
                except StopIteration:
                    if idx != 0: 
                        f.write(pre+'\n') # 最后一行不加逗号
                    break
            if idx not in logidx: 
                print('[ TABLE ] ==== dump_file: {} dump_number: {}.'.format(file, idx))
            f.write(']')

    if space is not None:
        tablespace = '{}:{}:{}'.format(defaults.VREDIS_DATA, taskid, space)
    else:
        tablespaces = []
        for table in sd.rds.keys('{}:{}*'.format(defaults.VREDIS_DATA, taskid)):
            tablespaces.append(table.decode())
        if len(tablespaces) == 0:
            print('no data.')
            return
        elif len(tablespaces) == 1:
            tablespace = tablespaces[0]
            space = tablespace.rsplit(':',1)[1]
        else:
            print('[ TIPS ] dump filename not set(-fi,--file), show the latest 10 data by default.')
            print('[ TIPS ] if set, default is -1(means all).')
            if file is not None:
                files = list(map(lambda file:file if file.endswith('.json') else file+'.json', file.split(',')))
                if len(files) != len(tablespaces):
                    print('[ WARNING! ] multiple table space dumps, you should use multiple tablespaces(use "," split ).')
                    print('[ WARNING! ] multiple table space dumps, pls ensure space_num == tables_num.')
                    print('[ WARNING! ][eg.] "vredis dump -ta 23 -sp tablespace1,tablespace2 -fi filename,filename2"')
                    print('[ WARNING! ][eg.] "vredis dump -ta 23 -fi filename,filename2" (simplify)')
                    print('[ TABLE ] tablespace number: {}'.format(len(tablespaces)))
                    for tablespace in tablespaces:
                        space = tablespace.rsplit(':',1)[1]
                        print('[ TABLE ] tablespace:{:>10}. collect number:{}.'.format(space,sd.rds.llen(tablespace)))
                elif len(set(files)) != len(files):
                    print('[ WARNING! ] make sure that all filenames are not duplicated.')
                else:
                    for tablespace,file in zip(tablespaces,files):
                        space = tablespace.rsplit(':',1)[1]
                        _dump(space,file)
            else:
                for tablespace in tablespaces:
                    space = tablespace.rsplit(':',1)[1]
                    print('[ TABLE ] tablespace:{}. collect number:{}.'.format(space,sd.rds.llen(tablespace)))
                    limit = limit if limit != -1 else 10
                    for idx,data in enumerate(_Table(sd, taskid, space, 'range', ignore_stop=True, limit=limit)):
                        print('{:>3}|'.format(idx+1),data)
            return

    if file is not None:
        _dump(space,file)
    else:
        print('[ TIPS ] dump filename not set, show the latest 10 data by default.')
        print('[ TIPS ] if set, default is -1(means all).')
        print('[ TABLE ] tablespace:{}.  collect number:{}.'.format(
            tablespace.rsplit(':',1)[1],sd.rds.llen(tablespace)))
        limit = limit if limit != -1 else 10
        for idx,data in enumerate(_Table(sd, taskid, space, 'range', ignore_stop=True, limit=limit)):
            print('{:>3}|'.format(idx+1),data)


def deal_with_version(args):
    print('vredis verison: {}'.format(__version__))


def deal_with_stat(args):
    host    = defaults_conf.get('host')
    port    = defaults_conf.get('port')
    password= defaults_conf.get('password')
    db      = defaults_conf.get('db')
    ls = int(args.list)
    la = int(args.latest)
    if args.taskid is None and args.error is None and not ls and not la:
        print(stat_description)
        print('pls set param:taskid for check task stat.')
        print('or set param:ls for check latest N task simple stat(default N is 5).')
        print('or set param:la for check latest task stat.')
        print('or set param:er for check latest N error info by taskid(default N is 100).')
        print('[eg.] "vredis stat -ta 23"')
        print('[eg.] "vredis stat -er 23"')
        print('[eg.] "vredis stat -er 23 -li 200"')
        print('[eg.] "vredis stat -la"')
        print('[eg.] "vredis stat -ls"')
        print('[eg.] "vredis stat -ls -li 10"')
        return
    sd = Sender.from_settings(host=host,port=port,password=password,db=db)
    if args.error is not None:
        li = 100 if args.limit == -1 else int(args.limit)
        er = int(args.error)
        table = '{}:{}'.format(defaults.VREDIS_TASK_ERROR, er)
        lens = sd.rds.llen(table)
        splitnum = 500
        cnt = 0
        cns = set()
        dpf = 0
        if lens>0:
            q = []
            for i in range(int(lens/splitnum)):
                v = [i*splitnum, i*splitnum+splitnum] if i==0 else [i*splitnum+1, i*splitnum+splitnum]
                q.append(v)
            if lens%splitnum != 0:
                if q:
                    q.append([q[-1][-1]+1, q[-1][-1]+lens%splitnum-1])
                else:
                    q.append([0,lens-1])
            else:
                q[-1][-1] = q[-1][-1] - 1
            for start,end in q:
                for ret in sd.rds.lrange(table,start,end):
                    cnt += 1
                    t = '| ERROR INDEX: {} |'.format(cnt)
                    v = json.loads(ret)
                    _num = 80
                    q = v.get('traceback').strip()
                    if q not in cns:
                        print()
                        print('-'*(_num//2))
                        cns.add(q)
                        for i in q.splitlines():
                            print('|', i)
                        print('-'*_num)
                        print('| taskid:  ',v.get('taskid'))
                        print('| function:',v.get('function'))
                        print('| args:    ',v.get('args'))
                        print('| kwargs:  ',v.get('kwargs'))
                        print('| plus:    ',v.get('plus'))
                        print('='*_num)
                        print(t)
                        print('='*len(t))
                    else:
                        dpf += 1
                    if cnt==li:
                        break
        _num = 40
        print()
        print('-'*_num)
        print('| *ALL ERROR NUM:',lens)
        print('| LOG ERROR NUM:',cnt,'(LIMIT:{})'.format(li))
        print('| LOG ERROR TYPE NUM:',len(cns))
        print('| LOG FILTER DUPLICATE ERROR NUM:',dpf)
        print('='*_num)
        print()
        return
    li = 5 if args.limit == -1 else int(args.limit)
    if ls or la:
        lp = []
        for i in sd.rds.hkeys(defaults.VREDIS_SENDER):
            i = i.decode()
            if '@' in i and i.endswith('hookcrash'):
                lp.append(int(i.split('@')[0]))
        if ls:
            fmt = '{:>7}  {:>20}  {:>10}  {:>7}  {:>5}  {}'
            print('[ INFO ] latest {} task simple stat'.format(li))
            print(fmt.format('taskid', 'task starttime', 'collection','execute','fail', 'workerids'))
            print('='*75)
            for taskid in sorted(lp)[::-1][:li]:
                timestamp   = sd.rds.hget(defaults.VREDIS_WORKER, '{}@stamp'.format(taskid))
                stampcut    = str(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(int(timestamp))))\
                                 if timestamp else str('non-task')
                workerids   = sd.rds.hget(defaults.VREDIS_SENDER, '{}@hookcrash'.format(taskid))
                workerids   = list(map(int,json.loads(workerids))) if workerids else workerids
                dt = sd.get_stat(taskid)
                if dt is not None:
                    collection,execute,fail,tasknum = dt.pop('all').values()
                else:
                    collection,execute,fail = None,None,None
                print(fmt.format(taskid, stampcut, collection,execute,fail, workerids))
            return
        elif la:
            if not lp:
                print('no task in redis.')
                return
            else:
                la = sorted(lp)[-1]
    taskid  = la if la else int(args.taskid)
    while True:
        stype = sd.rds.hget(defaults.VREDIS_SENDER,'{}@scripttype'.format(taskid))
        if stype:
            taskid -= 1
        elif taskid == 0:
            print('no task in redis.')
            return
        else:
            break
    info    = '[ REDIS ]'+'{:>36}'.format('host: {}, port: {}'.format(host,port))
    print(info)
    print('='*45)
    dt = sd.get_stat(taskid)
    if dt is None:
        print('no stat taskid:{}.'.format(taskid))
    else:
        # format print
        a = dt.pop('all')
        kt = sorted(dt,key=lambda i:int(i))
        fmt = '{:>9}'*5
        print(fmt.format('workerid','collect','execute','fail','stop'))
        print(fmt.format(*['------']*5))
        for idx,key in enumerate(kt):
            value = dt[key]
            fm = fmt.format(key,
                value['collection'],
                value['execute'],
                value['fail'],
                str(bool(value['stop'])))
            print(fm)
            if idx == len(dt) - 1:
                print(fmt.format(*['------']*5))
                print(fmt.format('taskid','collect','execute','fail','undistr'))
                key,value = taskid,a
                fm = fmt.format(key,
                    value['collection'],
                    value['execute'],
                    value['fail'],
                    value['tasknum'])
                print(fm)
    timestamp   = sd.rds.hget(defaults.VREDIS_WORKER, '{}@stamp'.format(taskid))
    stampinfo   = '{:>' + str(len(info)) +'}'
    stampcut    = str(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(int(timestamp)))) if timestamp else str(None)
    stampinfo   = stampinfo.format('start:{}'.format(stampcut))
    print('='*45)
    print(stampinfo)


def deal_with_cmdline(args):
    print('[ use CTRL+PAUSE(win)/ALT+PAUSE(linux) to break ]')
    host    = defaults_conf.get('host')
    port    = defaults_conf.get('port')
    password= defaults_conf.get('password')
    db      = defaults_conf.get('db')
    workerfilter= list(map(int,args.workerfilter.split(','))) if args.workerfilter!='all' else None
    print('[ REDIS ] host:{}, port:{}'.format(host,port))
    sd = Sender.from_settings(host=host,port=port,password=password,db=db)
    while True:
        cmd = input('cmd/ ')
        if cmd.strip():
            taskid = sd.send({'command':'cmdline','settings':{'VREDIS_CMDLINE':cmd,
                                                     'VREDIS_KEEP_LOG_CONSOLE':False,
                                                     'VREDIS_FILTER_WORKERID':workerfilter}},loginfo=False)
            sd.rds.hset(defaults.VREDIS_SENDER,'{}@scripttype'.format(taskid),'cmdline')
            while not sd.logstop:
                time.sleep(.15)


def deal_with_config(args):
    global defaults_conf
    clear = int(args.clear)
    if args.host     == None and\
       args.port     == None and\
       args.password == None and\
       args.db       == None:
        if clear:
            with open(config,'w',encoding='utf-8') as f:
                f.write(json.dumps(_o_conf,indent=4))
            print('config clear')
            print(json.dumps(_o_conf,indent=4))
        else:
            print('current defaults [use -cl/--clear clear this settings]:')
            print(json.dumps(defaults_conf,indent=4))
    else:
        _format_defaults = json.dumps(defaults_conf,indent=4)
        with open(config,'w',encoding='utf-8') as f:
            f.write(_format_defaults)
        print('current defaults [use -cl/--clear clear this settings]:')
        print(_format_defaults)


def test_deal(args):
    host    = defaults_conf.get('host')
    port    = defaults_conf.get('port')
    password= defaults_conf.get('password')
    db      = defaults_conf.get('db')
    workerfilter= args.workerfilter
    print(host,port,password,db,workerfilter)

def execute(argv=None):
    if argv is None: argv = sys.argv
    # 处理命令行
    parse = argparse.ArgumentParser(
        usage           = None,
        epilog          = None,
        formatter_class = argparse.RawDescriptionHelpFormatter,
        description     = h_description,
        add_help        = False)
    vct = vredis_command_types
    parse.add_argument('command',               choices=vct,        help=argparse.SUPPRESS)
    parse.add_argument('-ho','--host',          default=None,       help=argparse.SUPPRESS)
    parse.add_argument('-po','--port',          default=None,       help=argparse.SUPPRESS)
    parse.add_argument('-pa','--password',      default=None,       help=argparse.SUPPRESS)
    parse.add_argument('-db','--db',            default=None,       help=argparse.SUPPRESS)
    parse.add_argument('-wf','--workerfilter',  default='all',      help=argparse.SUPPRESS)
    parse.add_argument('-ta','--taskid',        default=None,       help=argparse.SUPPRESS)
    parse.add_argument('-cl','--clear',         action='store_true',help=argparse.SUPPRESS)
    parse.add_argument('-ls','--list',          action='store_true',help=argparse.SUPPRESS)
    parse.add_argument('-fo','--force',         action='store_true',help=argparse.SUPPRESS)
    parse.add_argument('-la','--latest',        action='store_true',help=argparse.SUPPRESS)
    parse.add_argument('-li','--limit',         default=-1,         help=argparse.SUPPRESS)
    parse.add_argument('-nt','--nthread',       default=32,         help=argparse.SUPPRESS)
    parse.add_argument('-er','--error',         default=None,       help=argparse.SUPPRESS)
    parse.add_argument('-sp','--space',         default=None,       help=argparse.SUPPRESS)
    parse.add_argument('-fi','--file',          default=None,       help=argparse.SUPPRESS)
    _print_help(argv)

    args = parse.parse_args()

    init_default(args)
    if   args.command == 'worker':  deal_with_worker(args)
    elif args.command == 'cmdline': deal_with_cmdline(args)
    elif args.command == 'stat':    deal_with_stat(args)
    elif args.command == 'stop':    deal_with_stop(args)
    elif args.command == 'config':  deal_with_config(args)
    elif args.command == 'version': deal_with_version(args)
    elif args.command == 'dump':    deal_with_dump(args)
    # else: test_deal(args)

if __name__ == '__main__':
    execute()