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

vredis_command_types = defaults.VREDIS_COMMAND_TYPES
vredis_command_types.remove('script') 
vredis_command_types = vredis_command_types + ['worker','stat','stop','config','dump','version']



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
  <command> -h|--help   ::show subcommand info
{}
defaults
  type<param>
  -ho,--host            ::redis host.           default: localhost
  -po,--port            ::redis port.           default: 6379
  -pa,--password        ::redis password.       default: None
  -db,--db              ::redis db.             default: 0
  -wf,--workerfilter    ::worker filter         default: all
                        ||this parameter can only work in cmdline mode.
  -ta,--taskid          ::check task work stat  default: None
                        ||this parameter can only work in stat mode.
  -li,--limit           ::dump data limit       default: -1 (all)
                        ||this parameter can only work in dump mode.
  -sp,--space           ::dump data space       default: 'default'
                        ||this parameter can only work in dump mode.
                        ||if not set, use default store space.
                        ||usually, you don't have to change the name here.
  -fi,--file            ::dump data filename
                        ||this parameter can only work in dump mode.
                        ||if set, try dump data in a file
                        ||if not set, just get data and show it in console.
  type<toggle>
  -cl,--clear           ::clear config, use initial configuration.
                        ||this parameter can only work in config mode.

[cmd info.]
  "vredis"              ::show default info
  "vredis -h"           ::show default info
  "vredis --help"       ::show all info
'''

cmdline_description = '''
  cmdline               ::[eg.] "vredis cmdline -wf 3,6,9"
    -wf --workerfilter  ||this parameter can only work in cmdline mode.
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
    -ta --taskid        ||this parameter can work in stat mode
'''

stop_description = '''
  stop                  ::[eg.] "vredis stop -ta 26"
    -ta --taskid        ||this parameter can work in stop mode
'''

dump_description = '''
  dump                  ::[eg.] "vredis stop -ta 26"
    -li,--limit         ::dump data limit       default: -1 (all)
                        ||this parameter can only work in dump mode.
    -sp,--space         ::dump data space       default: 'default'
                        ||this parameter can only work in dump mode.
                        ||if not set, use default store space.
                        ||usually, you don't have to change the name here.
    -fi,--file          ::dump toggle
                        ||this parameter can only work in dump mode.
                        ||if set, try dump data in a file
                        ||if not set, just get data and show it in console.
'''

worker_description = '''
  worker                ::[eg.] "vredis worker --host 192.168.0.77 --port 6666 --password vredis"
                        ||open a worker waiting task
                        ||all parameters of this command depend on default parameters
                        ::[eg.] "vredis worker"  
                        ||if vredis_config not set. 
                        ||worker use defaults parameters connect redis server
                        ||worker use host localhost
                        ||worker use port 6379
                        ||[ more info see defaults params ]
                        ::[eg.] "vredis worker -ho 192.168.0.77 -po 6666 -pa vredis"
                        ||worker use host "192.168.0.77"
                        ||worker use port 6666
                        ||worker use password vredis
'''

config_description = '''
  config                ::[eg.] "vredis config -ho xx.xx.xx.xx -po 6666 -pa vredis -db 1"
                        ||over write default config
                        ||it works in script and cmdtool.
                        ||cmd_config > vredis_config > init_config
                        ||cmd_config:       in cmdline
                        ||vredis_config:    over write defaults
                        ||init_config:      localhost:6379 passworl:None db:0
    -cl,--clear         ::clear config
                        ||this parameter can only work in config mode.
                        ||use init_config as defaults config
                        ||init_config:      localhost:6379 passworl:None db:0
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
        if argv[1] == '-h':     print(h_description)
        if argv[1] == '--help': print(help_description)
        sys.exit(0)


def deal_with_worker(args):
    print('[ use CTRL+PAUSE(win)/ALT+PAUSE(linux) to break ]')
    host    = defaults_conf.get('host')
    port    = defaults_conf.get('port')
    password= defaults_conf.get('password')
    db      = defaults_conf.get('db')
    print('[ REDIS ] host:{}, port:{}'.format(host,port))
    wk      = Worker.from_settings(host=host,port=port,password=password,db=db)
    wk.start()


def deal_with_stop(args):
    host    = defaults_conf.get('host')
    port    = defaults_conf.get('port')
    password= defaults_conf.get('password')
    db      = defaults_conf.get('db')
    if args.taskid is None:
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
    space   = args.space # 'default'
    file    = args.file # None
    if args.taskid is None:
        print('pls set param:taskid for dump task.')
        print('[eg.] "vredis dump -ta 23 -li 100 -fi some.json"')
        return
    taskid  = int(args.taskid)
    tablespace = '{}:{}:{}'.format(defaults.VREDIS_DATA, taskid, space)
    print('[ REDIS ] host:{}, port:{}'.format(host,port))
    sd      = Sender.from_settings(host=host,port=port,password=password,db=db)
    print('[ TABLE ] space:{}.'.format(space))
    print('[ TABLE ] all number:{}.'.format(sd.rds.llen(tablespace)))

    if file is not None:
        path,name = os.path.split(file)
        path      = path if path.strip() else os.getcwd()
        filepath  = os.path.join(path,name)
        with open(filepath,'a',encoding='utf-8') as f:
            f.write('[\n')
            idx = 0
            for idx,data in enumerate(_Table(sd, taskid, space, 'range', limit=limit),1):
                if idx%5000==0 and idx!=0:
                    print('dump number:{}.'.format(idx))
                f.write(json.dumps(data)+',\n')
            print('dump number:{}.'.format(idx))
            f.write(']')
    else:
        for data in _Table(sd, taskid, space, 'range', limit=limit):
            print(data)


def deal_with_version(args):
    print('vredis verison: {}'.format(__version__))


def deal_with_stat(args):
    host    = defaults_conf.get('host')
    port    = defaults_conf.get('port')
    password= defaults_conf.get('password')
    db      = defaults_conf.get('db')
    if args.taskid is None:
        print('pls set param:taskid for check task stat.')
        print('[eg.] "vredis stat -ta 23"')
        return
    taskid  = int(args.taskid)
    info    = '[ REDIS ]'+'{:>36}'.format('host: {}, port: {}'.format(host,port))
    print(info)
    print('='*45)
    sd      = Sender.from_settings(host=host,port=port,password=password,db=db)
    dt      = sd.get_stat(taskid)
    if dt is None:
        print('no stat taskid:{}.'.format(taskid))
    else:
        # format print
        a = dt.pop('all')
        kt = sorted(dt,key=lambda i:int(i))
        fmt = '{:>9}'*5
        print(fmt.format('taskid','collect','execute','fail','stop'))
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
                print(fmt.format('-','collect','execute','fail','undistr'))
                key,value = 'all',a
                fm = fmt.format(key,
                    value['collection'],
                    value['execute'],
                    value['fail'],
                    value['tasknum'])
                print(fm)
    timestamp   = sd.rds.hget(defaults.VREDIS_WORKER, '{}@stamp'.format(taskid))
    stampinfo   = '{:>' + str(len(info)) +'}'
    stampcut    = str(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(int(timestamp)))) if timestamp else str(None)
    stampinfo   = stampinfo.format('start: '+stampcut)
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
            sd.send({'command':'cmdline','settings':{'VREDIS_CMDLINE':cmd,
                                                     'VREDIS_KEEP_LOG_CONSOLE':False,
                                                     'VREDIS_FILTER_WORKERID':workerfilter}},loginfo=False)
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
    parse.add_argument('-li','--limit',         default=-1,         help=argparse.SUPPRESS)
    parse.add_argument('-sp','--space',         default='default',  help=argparse.SUPPRESS)
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