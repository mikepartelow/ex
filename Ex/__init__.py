# FIXME:
# See also POSIX users (Linux, BSD, etc.) are strongly encouraged to install and use the much more recent subprocess32 module
# instead of the version included with python 2.7. It is a drop in replacement with better behavior in many situations.

import subprocess, multiprocessing, time, signal, os, contextlib
import tempfile

# FIXME: make it work on windows :/
#        see how subprocess implements terminate() for windows, and do that.  or if possible through some magic,
#        call subprocess.Popen.terminate() directly and let them maintain the if/else logic
#       don't forget child procs
#
def sleepy_killer(sleep_seconds, pid_to_kill):
    # FIXME: kill child processes also
    #
    # FIXME: might as well make this work with logging.  we will eventually need to debug it, so make it loggable by default.
    #        note: the obvious solution is to pass in a logger obj from ex().  but we're in a separate process so that will only be a copy
    #              it probably works, but it's hard to test unless maybe we move to a file based logger
    #               will we end up with concurrency issues (scrambled logs) if we do that?
    time.sleep(sleep_seconds)
    os.kill(pid_to_kill, signal.SIGKILL)

@contextlib.contextmanager
def timeout_process(timeout_seconds, pid):
    if timeout_seconds > 0:
        killer = multiprocessing.Process(target=sleepy_killer, args=(timeout_seconds, pid))
        killer.start()
        yield
        killer.terminate()
        killer.join()
    else:
        yield

# the original:
# def ex(timeout, cmd, save_stdout=True, save_stderr=True, killmon=None, pidcb=None, no_log=True, env=None, username=None):

def ex(timeout_seconds, command, ignore_stderr=False, pid_callback=None, logger=None):
    # FIXME: When using shell=True, pipes.quote() can be used to properly escape whitespace and shell metacharacters in
    #        strings that are going to be used to construct shell commands.

    # separate implementations depending on expected size of output (size hint argument)?
    #   see SpooledTemporaryFile!  STF is only good until we call fileno(), which happens first thing in sp.Popen()
    #     otherwise, it's perfect :/

    stderr_arg = None if ignore_stderr else subprocess.STDOUT

    with contextlib.closing(tempfile.TemporaryFile()) as outfile:
        if logger is not None:
            logger.info('ex(%d, "%s")', timeout_seconds, command)

        p = subprocess.Popen(command, shell=True, stderr=stderr_arg, stdout=outfile)

        if pid_callback is not None:
            pid_callback(p.pid)

        with timeout_process(timeout_seconds, p.pid):
            exit_code = p.wait()

        outfile.seek(0)

        return exit_code, outfile.read()