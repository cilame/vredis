import sys
import argparse
import re
import time

from . import defaults
from .worker import Worker
from .sender import Sender

vredis_command_types = defaults.VREDIS_COMMAND_TYPES
vredis_command_types.remove('script') 
vredis_command_types = vredis_command_types + ['worker']

description = '''
usage
  vredis <command> [options] [args]

command
  list      show worker info.
  run       run.
  attach    attach.
  cmdline   use cmdline connect host.
  worker    start a worker.
  <command> -h|--help   ::show subcommand info
{}
defaults
  -ho,--host            ::redis host.                       default: localhost
  -po,--port            ::redis port.                       default: 6379
  -pa,--password        ::redis password.                   default: None
  -db,--db              ::redis db.                         default: 0
  -n,-wn,--workermaxnum ::worker max numb, esay for use.    default: all
  -w,-wf,--workerfilter ::[separated by ','] worker filter  default: all

[cmd info.]
  vredis                ::show default info
  vredis -h             ::show default info
  vredis --help         ::show all info
'''

list_description = '''
  list                  ::[eg.] "vredis list --stat"
    --stat
    --collection
'''

cmdline_description = '''
  cmdline               ::[eg.] "vredis cmdline -wf 3,6,9"
    -wf --workerfilter
'''

worker_description = '''
  worker                ::[eg.] "vredis worker -ho 192.168.0.77 -po 6666 -pa vilame"
    all parameters of this command depend on default parameters
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
help_description = description.format(''.join([list_description,
                                               cmdline_description,
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
    wk = Worker.from_settings(host=host,port=port,password=password,db=db)
    wk.start()

def deal_with_cmdline(args):
    print('[ use CTRL+PAUSE to break ]')
    host        = args.host
    port        = int(args.port)
    password    = args.password
    db          = int(args.db)
    workerfilter= list(map(int,args.workerfilter.split(','))) if args.workerfilter!='all' else None
    sd = Sender.from_settings(host=host,port=port,password=password,db=db)
    while True:
        cmd = input('cmd/ ')
        if cmd.strip():
            sd.send({'command':'cmdline','settings':{'VREDIS_CMDLINE':cmd,
                                                     'VREDIS_KEEP_LOG_CONSOLE':False,
                                                     'VREDIS_FILTER_WORKERID':workerfilter}},loginfo=True)
            while not sd.logstop:
                time.sleep(.15)

def test_deal(args):
    host        = args.host
    port        = int(args.port)
    password    = args.password
    db          = int(args.db)
    workerfilter= args.workerfilter
    workermaxnum= args.workermaxnum
    print(host,port,password,db,workerfilter,workermaxnum)

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
    parse.add_argument('-w','-wf','--workerfilter', default='all',                  help=argparse.SUPPRESS) # w和n互斥
    parse.add_argument('-n','-wn','--workermaxnum', default='all',                  help=argparse.SUPPRESS)

    _print_help(argv)

    args = parse.parse_args()
    if   args.command == 'worker':  deal_with_worker(args)
    elif args.command == 'cmdline': deal_with_cmdline(args)

if __name__ == '__main__':
    execute()