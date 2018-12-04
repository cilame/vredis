import sys

__org_stdout__ = sys.stdout
__org_stderr__ = sys.stderr
class hook_stdout:
    def __init__(self,func):
        self.hookfunc = func
    def write(self,text):
        self.hookfunc(text)
        __org_stdout__.write(text)
    def flush(self):
        __org_stdout__.flush()
class hook_stderr:
    def __init__(self,func):
        self.hookfunc = func
    def write(self,text):
        self.hookfunc(text)
        __org_stderr__.write(text)
    def flush(self):
        __org_stderr__.flush()

def hook_console(func):
    sys.stdout = hook_stdout(func)
    sys.stderr = hook_stderr(func)

def unhook_console():
    sys.stdout = __org_stdout__
    sys.stderr = __org_stderr__