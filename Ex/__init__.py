# FIXME: pydoc, docstrings (see /usr/lib/python2.7/subprocess.py)

# FIXME: make it work on windows :/

# FIXME:
# See also POSIX users (Linux, BSD, etc.) are strongly encouraged to install and use the much more recent subprocess32 module
# instead of the version included with python 2.7. It is a drop in replacement with better behavior in many situations.

import subprocess, multiprocessing, time, signal, os, contextlib, logging, tempfile, pipes, shlex, types
import psutil

# the original:
# def ex(timeout, cmd, save_stdout=True, save_stderr=True, killmon=None, pidcb=None, no_log=True, env=None, username=None):

# TODO: in futuristic mode, don't read() -- let the caller do it if he cares! (will conflict with closing())
# TODO: the previous idea of "killmon" is probably useful, if not essential.  a callback that is called periodically, with a True return
#       resulting in termination of our process
#

def ex(timeout_seconds, command, ignore_stderr=False, pid_callback=None, logger=logging.getLogger('mikep.ex'), buffer_output_in_memory=False):
    if logger is not None:
        logger.info('ex(%d, "%s")', timeout_seconds, command)

    exit_code = None
    stderr_arg = None if ignore_stderr else subprocess.STDOUT

    with _fancy_spawn(command, stderr_arg, buffer_output_in_memory) as p:
        with _log_wait_raise(logger, p):
            if pid_callback is not None:
                pid_callback(p.pid)

            with _terminate_process_after_timeout(timeout_seconds, p.pid, logger):
                exit_code = p.wait()

        return exit_code, p.fetch_output()


# FIXME: maybe use sudo iff an env var asks for it, OR just blame the OS/user for leaks and demand upgrades.
#
# FIXME: can anything be done about the hideous try/except/else cascade?
def _sleepy_killer(sleep_seconds, pid_to_kill, logger):
    logger.debug("_sleepy_killer's pid: %d", os.getpid())
    time.sleep(sleep_seconds)

    parent = psutil.Process(pid_to_kill)
    children = parent.children(recursive=True)
    child_pids = map(lambda p: p.pid, children)

    logger.debug("_sleepy_killer beginning massacre of %d family (%s) after %d seconds", pid_to_kill, str(child_pids), sleep_seconds)

    # terminate the child processes "bottom up"
    for child in reversed(children):
        logger.debug("_sleepy_killer terminating child %d of %d family", child.pid, pid_to_kill)
        try:
            child.terminate()
        except:
            logger.exception("error while terminating child %d", child.pid)

    # to avoid deadlocks, wait until all child processes have been terminated before waiting on any of them.
    for child in children:
        logger.debug("_sleepy_killer terminated child %d of %d family", child.pid, pid_to_kill)
        try:
            child.wait()
        except:
            logger.exception("error while waiting child %d", child.pid)
        else:
            logger.debug("_sleepy_killer waited child %d of %d family", child.pid, pid_to_kill)

    logger.debug("_sleepy_killer terminating parent %d", pid_to_kill)
    try:
        parent.terminate()
    except:
        logger.exception("error while terminating parent %d", parent.pid)
    else:
        logger.debug("_sleepy_killer terminated parent %d", pid_to_kill)
        try:
            parent.wait()
        except:
            logger.exception("error while waiting parent %d", parent.pid)
        else:
            logger.debug("_sleepy_killer waited on parent %d", pid_to_kill)

@contextlib.contextmanager
def _terminate_process_after_timeout(timeout_seconds, pid, logger):
    if timeout_seconds > 0:
        killer = multiprocessing.Process(target=_sleepy_killer, args=(timeout_seconds, pid, logger))
        killer.start()
        try:
            yield
        finally:
            try:
                killer.terminate()
            except NoSuchProcess:
                pass
            killer.join()
    else:
        yield

@contextlib.contextmanager
def _log_wait_raise(logger, process):
    try:
        yield
    except:
        if logger is not None:
            logger.exception("ex exception")

        if process.poll() is None:
            process.terminate()
            process.wait()

        raise

def _pipe_output_reader(self):
    return self.stdout.read()

def _file_output_reader(self):
    self._outfile.seek(0)
    return self._outfile.read()

@contextlib.contextmanager
def _fancy_spawn(command, stderr_arg, buffer_output_in_memory):
    # this minor monstrosity exists to smooth out the differences between using a subprocess.PIPE and a regular file with Popen
    #
    if buffer_output_in_memory is True:
        outfile = subprocess.PIPE
    else:
        outfile = tempfile.TemporaryFile()

    try:
        p = subprocess.Popen(command, shell=True, stderr=stderr_arg, stdout=outfile)

        if buffer_output_in_memory is True:
            p.fetch_output = types.MethodType(_pipe_output_reader, p)
        else:
            p._outfile = outfile
            p.fetch_output = types.MethodType(_file_output_reader, p)

        yield p

    finally:
        if buffer_output_in_memory is not True:
            outfile.close()
