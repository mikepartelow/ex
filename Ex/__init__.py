# FIXME:
# See also POSIX users (Linux, BSD, etc.) are strongly encouraged to install and use the much more recent subprocess32 module
# instead of the version included with python 2.7. It is a drop in replacement with better behavior in many situations.

import subprocess, multiprocessing, time, signal, os, contextlib

# FIXME: make it work on windows :/
#
def sleepy_killer(sleep_seconds, pid_to_kill):
    time.sleep(sleep_seconds)
    # FIXME: kill child processes also
    #
    os.kill(pid_to_kill, signal.SIGKILL)

@contextlib.contextmanager
def timeout_process(timeout_seconds, pid):
    if timeout_seconds > 0:
        killer = multiprocessing.Process(target=sleepy_killer, args=(timeout_seconds, pid,))
        killer.start()
        yield
        killer.join()
    else:
        yield

def ex(timeout_seconds, command):
    # FIXME: When using shell=True, pipes.quote() can be used to properly escape whitespace and shell metacharacters in
    #        strings that are going to be used to construct shell commands.
    the_process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    with timeout_process(timeout_seconds, the_process.pid):
        output = the_process.stdout.read()

    exit_code = the_process.wait()

    return exit_code, output