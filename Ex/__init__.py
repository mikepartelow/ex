# FIXME:
# See also POSIX users (Linux, BSD, etc.) are strongly encouraged to install and use the much more recent subprocess32 module
# instead of the version included with python 2.7. It is a drop in replacement with better behavior in many situations.

import subprocess, multiprocessing, time, signal, os, contextlib
import tempfile

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
        killer.terminate()
        killer.join()
    else:
        yield

def ex(timeout_seconds, command):
    # FIXME: When using shell=True, pipes.quote() can be used to properly escape whitespace and shell metacharacters in
    #        strings that are going to be used to construct shell commands.

    # separate implementations depending on expected size of output (size hint argument)?
    #   see SpooledTemporaryFile!  STF is only good until we call fileno(), which happens first thing in sp.Popen()
    #     otherwise, it's perfect :/

    with contextlib.closing(tempfile.TemporaryFile()) as outfile:
        p = subprocess.Popen(command, shell=True, stderr=subprocess.STDOUT, stdout=outfile)

        with timeout_process(timeout_seconds, p.pid):
            exit_code = p.wait()

        outfile.seek(0)

        return exit_code, outfile.read()