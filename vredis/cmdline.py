import sys
import argparse
import re

from . import defaults
VREDIS_COMMAND_TYPES = defaults.VREDIS_COMMAND_TYPES

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
  --host                ::redis host. default: localhost
  --host                ::redis port. default: 6379
  -n,-wn,--workermaxnum ::worker max numb, esay for use.
  -w,-wf,--workerfilter ::worker filter

{}

epilog
------------------------------------------
  .
'''

list_description = '''
list <command> eg. "vredis list --stat"
------------------------------------------
  --stat
  --collection
'''

cmdline_description = '''
cmdline <command> eg. "vredis cmdline -wf 3,6,9"
------------------------------------------
  -wf --workerfilter
'''


h_description = re.sub('\{\}\n','',description).strip()
help_description = description.format(''.join([list_description,
                                               cmdline_description])).strip()



def _print_help(argv):
    if len(argv) == 1:
        print(h_description)
        sys.exit(0)
    if len(argv) == 2 and \
           argv[1] in ['-h','--help']:
        if argv[1] == '-h':     print(h_description)
        if argv[1] == '--help': print(help_description)
        sys.exit(0)

def execute(argv=None):
    if argv is None: argv = sys.argv
    # 处理命令行
    parse = argparse.ArgumentParser(
        usage           = None,
        epilog          = None,
        formatter_class = argparse.RawDescriptionHelpFormatter,
        description     = h_description,
        add_help        = False)
    parse.add_argument('command',                   choices=VREDIS_COMMAND_TYPES,   help=argparse.SUPPRESS)
    parse.add_argument('--host',                    default='localhost',            help=argparse.SUPPRESS)
    parse.add_argument('--port',                    default='6379',                 help=argparse.SUPPRESS)
    parse.add_argument('-w','-wf','--workerfilter', default='all',                  help=argparse.SUPPRESS) # w和n互斥
    parse.add_argument('-n','-wn','--workermaxnum', default='all',                  help=argparse.SUPPRESS)

    _print_help(argv)

    args = parse.parse_args()
    

if __name__ == '__main__':
    execute()