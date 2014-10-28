# FIXME:
# See also POSIX users (Linux, BSD, etc.) are strongly encouraged to install and use the much more recent subprocess32 module
# instead of the version included with python 2.7. It is a drop in replacement with better behavior in many situations.

import subprocess, multiprocessing, time, signal, os, contextlib, logging, tempfile
import psutil

# FIXME: make it work on windows :/
# FIXME: maybe use sudo iff an env var asks for it, OR just blame the OS/user for leaks and demand upgrades.
#
def sleepy_killer(sleep_seconds, pid_to_kill, logger):
    time.sleep(sleep_seconds)

    logger.debug("sleepy_killer beginning massacre of %d family after %d seconds", pid_to_kill, sleep_seconds)

    parent = psutil.Process(pid_to_kill)
    for child in parent.children(recursive=True):
        child.terminate()
        logger.debug("sleepy_killer terminated child %d of %d family", child.pid, pid_to_kill)
        child.wait()
        logger.debug("sleepy_killer waited child %d of %d family", child.pid, pid_to_kill)

    parent.terminate()
    logger.debug("sleepy_killer terminated parent %d", pid_to_kill)
    parent.wait()
    logger.debug("sleepy_killer waited on parent %d", pid_to_kill)

@contextlib.contextmanager
def timeout_process(timeout_seconds, pid, logger):
    if timeout_seconds > 0:
        killer = multiprocessing.Process(target=sleepy_killer, args=(timeout_seconds, pid, logger))
        killer.start()
        try:
            yield
        finally:
            killer.terminate()
            killer.join()
    else:
        yield

@contextlib.contextmanager
def log_wait_raise(logger, process):
    try:
        yield
    except:
        if logger is not None:
            logger.exception("ex exception")

        if process.poll() is None:
            process.terminate()
            process.wait()

        raise


# the original:
# def ex(timeout, cmd, save_stdout=True, save_stderr=True, killmon=None, pidcb=None, no_log=True, env=None, username=None):

def ex(timeout_seconds, command, ignore_stderr=False, pid_callback=None, logger=logging.getLogger('mikep.ex')):
    exit_code, output = None, None

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

        with log_wait_raise(logger, p):
            if pid_callback is not None:
                pid_callback(p.pid)

            with timeout_process(timeout_seconds, p.pid, logger):
                exit_code = p.wait()

        outfile.seek(0)
        output = outfile.read() # TODO: in futuristic mode, don't read() -- let the caller do it if he cares! (will conflict with closing())

        return exit_code, output