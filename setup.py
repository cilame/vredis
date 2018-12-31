from setuptools import setup, find_packages  
import sys  
  
setup(  
    name="vredis",
    version="0.0.0",
    author="cilame",
    author_email="opaquism@hotmail.com",
    description="Distributed script crawler framework.",
    entry_points={
        'console_scripts': ['vredis = vredis.cmdline:execute']
    },
    long_description=r"""
Distributed script crawler framework.
=====================================

.. code-block:: python

    # Simply connecting redis on the worker side of the library provides an-
    # executable power for distributed scripts
    # All function executions on the sender end will be piped to redis, 
    # and the worker end will be pulled out of the pipe to execute.
    # Support multi-task simultaneous execution! Each execution maintains a taskid, 
    # and different tasks maintain their configuration space according to the-
    # taskid when they are executed simultaneously.

worker
======

.. code-block:: python

    import vredis
    s = vredis.Worker.from_settings(host='xx.xx.xx.xx',port=6666,password='vilame')
    s.start()

    # bash
    C:\Users\Administrator>vredis worker -ho xx.xx.xx.xx -po 6666 -pa vilame -db 0
    # if not set param. use defaults param.
    # default host localhost
    # default port 6379
    # default password None
    # default db 0

sender
======

.. code-block:: python

    from vredis import pipe

    pipe.connect(host='xx.xx.xx.xx',port=6666,password='vilame')
    pipe.DEBUG = True # True/False. worker prints on the worker_console.

    # very low code intrusion, no decorator or even complete barrier-free execution
    # The decorated function becomes a send function and is sent to the task pipeline
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
        some(i)
        some2(i)

""",
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/cilame/vredis",
    packages=['vredis'],
    classifiers=[
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
    ]
)  
