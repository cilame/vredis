import sys
import argparse

VREDIS_COMMAND_TYPES = ['list','run','attach','script'] 

description = '''
vredis <command> [options] [args]

command
------------------------------------------
  list      show info.
  run       run.
  cmdline   use cmdline connect host.
  script    script.
  attach    attach.

  <command> -h|--help   ::show subcommand info

defaults
------------------------------------------
  --host    redis host. default: localhost
  --host    redis port. default: 6379

'''

epilog = '''

epilog
------------------------------------------
  .

'''

def execute():

    # 处理命令行
    parse = argparse.ArgumentParser(
        usage           = None,
        epilog          = epilog,
        formatter_class = argparse.RawDescriptionHelpFormatter,
        description     = description,
        add_help        = False)
    parse.add_argument('command',choices=VREDIS_COMMAND_TYPES,help=argparse.SUPPRESS)
    parse.add_argument('--host',default='localhost',help=argparse.SUPPRESS)
    parse.add_argument('--port',default='6379',help=argparse.SUPPRESS)
    parse.add_argument('--filter',default=None,help=argparse.SUPPRESS)

    if   len(sys.argv) == 1 or \
        (len(sys.argv) == 2 and \
             sys.argv[1] in ['-h','--help']):
        parse.print_help()
        sys.exit(0)

    args = parse.parse_args()
    
