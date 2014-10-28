# FIXME:
# See also POSIX users (Linux, BSD, etc.) are strongly encouraged to install and use the much more recent subprocess32 module
# instead of the version included with python 2.7. It is a drop in replacement with better behavior in many situations.

import subprocess, multiprocessing, time, signal, os, contextlib, logging, tempfile, pipes, shlex
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

class StrikinglySimilarToAFile(object): pass

@contextlib.contextmanager
def homogenized_output_object(use_pipe):
    if use_pipe:
        f = StrikinglySimilarToAFile()
        f.fileno = subprocess.PIPE
    else:
        f = tempfile.TemporaryFile()

    try:
        yield f
    finally:
        if not use_pipe:
            f.close()


# the original:
# def ex(timeout, cmd, save_stdout=True, save_stderr=True, killmon=None, pidcb=None, no_log=True, env=None, username=None):

# TODO: in futuristic mode, don't read() -- let the caller do it if he cares! (will conflict with closing())

def ex(timeout_seconds, command, ignore_stderr=False, pid_callback=None, logger=logging.getLogger('mikep.ex'), buffer_output_in_memory=False):
    if logger is not None:
        logger.info('ex(%d, "%s")', timeout_seconds, command)

    exit_code, output = None, None
    stderr_arg = None if ignore_stderr else subprocess.STDOUT

    with homogenized_output_object(buffer_output_in_memory is True) as outfile:
        p = subprocess.Popen(command, shell=True, stderr=stderr_arg, stdout=outfile)

        with log_wait_raise(logger, p):
            if pid_callback is not None:
                pid_callback(p.pid)

            with timeout_process(timeout_seconds, p.pid, logger):
                exit_code = p.wait()

        if memory_buffer is False:
            outfile.seek(0)
            output = outfile.read()
        else:
            output = p.stdout.read()

        return exit_code, output