import platform

def list_command(cls, taskid, workerid, order):
    subcommand = order['subcommand']
    # subcommand 有两个功能
    if subcommand == None:
        subcommand = {'alive':'platform'}

    if list(subcommand)[0] == 'alive':
        d = []
        for i in subcommand['alive'].split():
            # 目前暂时只有平台类型的回显
            if i.strip().lower() == 'platform':
                d.append(str(platform.platform()))
        print(' '.join(d))

    if list(subcommand)[0] == 'check':
        # 这里的展示需要考虑到执行状态的展示，所以需要在考虑正式任务执行的状态收集之后再对这里进行开发。
        raise 'UnDevelopment'



def list_command_parse():

    pass

