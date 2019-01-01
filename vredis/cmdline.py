import sys
import argparse
import re
import time

from . import defaults
from .worker import Worker
from .sender import Sender

vredis_command_types = defaults.VREDIS_COMMAND_TYPES
vredis_command_types.remove('script') 
vredis_command_types = vredis_command_types + ['worker','stat']

description = '''
usage
  vredis <command> [options] [args]

command
  stat      use taskid check task work stat.
  cmdline   use cmdline connect host. and sent simple bash command.
  worker    start a worker.
  <command> -h|--help   ::show subcommand info
{}
defaults
  -ho,--host            ::redis host.                       default: localhost
  -po,--port            ::redis port.                       default: 6379
  -pa,--password        ::redis password.                   default: None
  -db,--db              ::redis db.                         default: 0
  -wf,--workerfilter    ::[separated by ','] worker filter  default: all
                        ||this parameter can only work in cmdline mode.
  -ta,--taskid          ::check task work stat              default: None
                        ||this parameter can only work in stat mode.

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
    -ta --taskid        ||this parameter can only work in stat mode
                        ||this command does not consume taskid
'''

worker_description = '''
  worker                ::[eg.] "vredis worker --host 192.168.0.77 --port 6666 --password vilame"
                        ||open a worker waiting task
                        ||all parameters of this command depend on default parameters
    cmd: "vredis worker"   
                        ::worker use defaults parameters connect redis server
                        ||worker use host localhost
                        ||worker use port 6379
                        ||[ more info see defaults params ]
    cmd: "vredis worker -ho 192.168.0.77 -po 6666 -pa vilame"
                        ::worker use host "192.168.0.77"
                        ||worker use port 6666
                        ||worker use password vilame
'''


h_description = re.sub('\{\}','',description).strip()
help_description = description.format(''.join([cmdline_description,
                                               stat_description,
                                               worker_description])).strip()



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
    print('[ use CTRL+PAUSE to break ]')
    host        = args.host
    port        = int(args.port)
    password    = args.password
    db          = int(args.db)
    print('[ REDIS-SERVER ] host:{}, port:{}'.format(host,port))
    wk = Worker.from_settings(host=host,port=port,password=password,db=db)
    wk.start()


def deal_with_stat(args):
    host        = args.host
    port        = int(args.port)
    password    = args.password
    db          = int(args.db)
    if args.taskid is None:
        print('pls set param:taskid for check task stat.')
        print('[eg.] "vredis stat -ta 23"')
        return
    taskid      = int(args.taskid)
    print('[ REDIS-SERVER ] host:{}, port:{}'.format(host,port))
    sd = Sender.from_settings(host=host,port=port,password=password,db=db)
    dt = sd.get_stat(taskid)
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
                print(fmt.format('-','collect','execute','fail','unstart'))
                key,value = 'all',a
                fm = fmt.format(key,
                    value['collection'],
                    value['execute'],
                    value['fail'],
                    value['tasknum'])
                print(fm)


def deal_with_cmdline(args):
    print('[ use CTRL+PAUSE to break ]')
    host        = args.host
    port        = int(args.port)
    password    = args.password
    db          = int(args.db)
    workerfilter= list(map(int,args.workerfilter.split(','))) if args.workerfilter!='all' else None
    print('[ REDIS-SERVER ] host:{}, port:{}'.format(host,port))
    sd = Sender.from_settings(host=host,port=port,password=password,db=db)
    while True:
        cmd = input('cmd/ ')
        if cmd.strip():
            sd.send({'command':'cmdline','settings':{'VREDIS_CMDLINE':cmd,
                                                     'VREDIS_KEEP_LOG_CONSOLE':False,
                                                     'VREDIS_FILTER_WORKERID':workerfilter}},loginfo=False)
            while not sd.logstop:
                time.sleep(.15)

def test_deal(args):
    host        = args.host
    port        = int(args.port)
    password    = args.password
    db          = int(args.db)
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
    parse.add_argument('command',                   choices=vredis_command_types,   help=argparse.SUPPRESS)
    parse.add_argument('-ho','--host',              default='localhost',            help=argparse.SUPPRESS)
    parse.add_argument('-po','--port',              default=6379,                   help=argparse.SUPPRESS)
    parse.add_argument('-pa','--password',          default=None,                   help=argparse.SUPPRESS)
    parse.add_argument('-db','--db',                default=0,                      help=argparse.SUPPRESS)
    parse.add_argument('-wf','--workerfilter',      default='all',                  help=argparse.SUPPRESS)
    parse.add_argument('-ta','--taskid',            default=None,                   help=argparse.SUPPRESS)

    _print_help(argv)

    args = parse.parse_args()
    if   args.command == 'worker':  deal_with_worker(args)
    elif args.command == 'cmdline': deal_with_cmdline(args)
    elif args.command == 'stat':    deal_with_stat(args)

if __name__ == '__main__':
    execute()