import unittest
import time
from Ex import ex

from contextlib import contextmanager
from datetime import datetime
import time
import logging
import os, tempfile
import subprocess

class PidMemorizer(object):
    def __init__(self):
        self.pid = None

    def __call__(self, the_pid):
        self.pid = the_pid

class Timer(object):
    def start(self):
        self.start_time = datetime.today()

    def stop(self):
        self.stop_time = datetime.today()

    @property
    def elapsed(self):
        return self.stop_time - self.start_time

@contextmanager
def timed(timer):
    timer.start()
    yield
    timer.stop()

@contextmanager
def stfu():
    try:
        yield
    except:
        pass

def delete_even_if_it_doesnt_exist(path):
    subprocess.call("rm -rf {}".format(path), shell=True)

class ExTest(unittest.TestCase):
    RANDOM_MEGABYTES_OF_STDOUT_CMD = "dd if=/dev/urandom of=/dev/stdout bs=1048576 count={} 2>/dev/null"
    LOG_PATH = os.path.join(tempfile.gettempdir(), 'ex_tests.log')

    def setUp(self):
        self.timer = Timer()
        delete_even_if_it_doesnt_exist(self.LOG_PATH)
        self.logger = logging.getLogger('mikep.ex')

    def tearDown(self):
        delete_even_if_it_doesnt_exist(self.LOG_PATH)

    def test_exit_code(self):
        r, out = ex(0, "exit 1")
        self.assertEqual(r, 1)

        r, out = ex(0, "exit 8")
        self.assertEqual(r, 8)

    def test_stdout(self):
        r, out = ex(0, 'echo "hello world"')
        self.assertEqual(out, "hello world\n")

        r, out = ex(0, 'echo "hello world" ; echo "goodbye world"')
        self.assertEqual(out, "hello world\ngoodbye world\n")

    def test_combined_stdout_stderr(self):
        r, out = ex(0, 'echo "hello world" 1>&2 ; echo "goodbye world"')
        self.assertEqual(out, "hello world\ngoodbye world\n")

    def test_ignored_stderr(self):
        r, out = ex(0, 'echo "hello world" 1>&2 ; echo "goodbye world"', ignore_stderr=True)
        self.assertEqual(out, "goodbye world\n")

    def test_large_output(self):
        megabytes = 8
        r, out = ex(0, self.RANDOM_MEGABYTES_OF_STDOUT_CMD.format(megabytes))
        self.assertEqual(len(out), 1024 * 1024 * megabytes)

    def test_timeout(self):
        with timed(self.timer):
            r, out = ex(2, "sleep 8")

        self.assertEqual(2, self.timer.elapsed.seconds)

    def test_timeout_output(self):
        with timed(self.timer):
            # we have to ignore stderr here because bash prints out a termination message
            r, out = ex(2, 'echo "hello world" ; sleep 4', ignore_stderr=True)

        self.assertEqual(2, self.timer.elapsed.seconds)
        self.assertEqual(out, "hello world\n")

    def test_no_timeout(self):
        with timed(self.timer):
            r, out = ex(0, 'echo "hello world" ; sleep 1')

        self.assertEqual(1, self.timer.elapsed.seconds)
        self.assertEqual(out, "hello world\n")

    def test_pid_callback(self):
        pm = PidMemorizer()
        self.assertIsNone(pm.pid)
        r, out = ex(0, 'echo "hello world"', pid_callback=pm)
        self.assertIsNotNone(pm.pid)

    def test_logging(self):
        command = 'echo "hello world"'
        self.logger.addHandler(logging.FileHandler(self.LOG_PATH))
        self.logger.setLevel(logging.DEBUG)
        r, out = ex(0, command, logger=self.logger)
        log_text = open(self.LOG_PATH).read()
        self.assertGreater(len(log_text), 0)

    def test_pid_kill_logging(self):
        pm = PidMemorizer()
        self.logger.addHandler(logging.FileHandler(self.LOG_PATH))
        self.logger.setLevel(logging.DEBUG)
        r, out = ex(2, "sleep 8", pid_callback=pm, logger=self.logger)
        log_text = open(self.LOG_PATH).read()
        self.assertIn(str(pm.pid), log_text)

    def test_pid_callback_exception_handling(self):
        self.logger.addHandler(logging.FileHandler(self.LOG_PATH))
        self.logger.setLevel(logging.DEBUG)

        with timed(self.timer):
            with self.assertRaises(ZeroDivisionError):
                r, out = ex(0, "sleep 8", pid_callback=lambda x: 2/0)

        self.assertEqual(0, self.timer.elapsed.seconds)
        log_text = open(self.LOG_PATH).read()
        self.assertIn('ZeroDivisionError', log_text)

    def test_child_process_death(self):
        child_count = 2
        pid_dir = tempfile.mkdtemp()

        with timed(self.timer):
            r, out = ex(2, "python tests/breeder.py {} {}".format(child_count, pid_dir))

        self.assertEqual(2, self.timer.elapsed.seconds)
        for pid_file in os.listdir(pid_dir):
            pid = int(pid_file)

            pid_absent = False
            try:
                os.kill(pid, 0)
            except OSError as e:
                pid_absent = (e.errno == 3)

            self.assertTrue(pid_absent)

    def test_that_output_temp_file_is_deleted(self):
        original_tempdir = tempfile.gettempdir()
        try:
            tempfile.tempdir = os.path.join(original_tempdir, 'ttotfid')
            with stfu():
                os.makedirs(tempfile.tempdir)
            self.assertEqual([], os.listdir(tempfile.tempdir))

            r, out = ex(0, 'echo "hello world"')
            self.assertEqual(out, "hello world\n")
            self.assertEqual([], os.listdir(tempfile.tempdir))
        finally:
            tempfile.tempdir = original_tempdir


    def test_memory_output_buffer(self):
        # NOTE : no point in testing performance.  performance testing is a separate issue.
        #        unit tests are here to ensure the interface *works*.  as long as setting this flag doesn't
        #        unexpectedly change the behavior, the performance is irrelevant.
        #
        r, out = ex(0, 'echo "hello world"', buffer_output_in_memory=True)
        self.assertEqual(out, "hello world\n")

        r, out = ex(0, 'echo "hello world" 1>&2 ; echo "goodbye world"', buffer_output_in_memory=True)
        self.assertEqual(out, "hello world\ngoodbye world\n")

        with timed(self.timer):
            # we have to ignore stderr here because bash prints out a termination message
            r, out = ex(2, 'echo "hello world" ; sleep 4', ignore_stderr=True, buffer_output_in_memory=True)

        self.assertEqual(2, self.timer.elapsed.seconds)
        self.assertEqual(out, "hello world\n")

    @unittest.skip("niy")
    def test_that_killer_exits(self):
        # 1) after killing the timed-out process
        # 2) if the process completes before timeout
        # shouldn't be too hard: add a useful "i'm killer and my pid is xyz" debug message, parse the log here, then check for pid.
        self.fail("niy")

    @unittest.skip("niy")
    def test_output_buffering(self):
        # make sure lines arrive in a timely manner # note: what does this even mean?  and what about osokine's complaint:
        #  if he's calling out = Ex("long process") ; print out ; long process will have to complete before output is ready.  what else?
        #
        #  maybe an interface to allow the caller direct access to stdout/stderr pipes would satisfy this request.
        #

        self.fail("niy")

    @unittest.skip("niy")
    def test_futuristic_timeouts(self):
        # we probably should return -9 for backcompat
        # but we should also have some way to differentiate between ex's exit code and the subprocesses' exit code
        #  possible solution: r is an object that is castable to int, but is not an int.
        #      r, out = ex(2, "sleep 8")
        #      self.assertEqual(-9, r)
        #      self.assertTrue(r.timed_out)
        #
        #  even better, make the backcompat behavior opt-in:
        #      r = ex(2, "sleep 8")
        #      self.assertNone(r.exit_code)
        #      self.assertEqual(r.output, '')
        #      self.assertTrue(r.timed_out)
        #      r, out = ex(2, "sleep 8", old_style_r=True)
        #      self.assertEqual(r, -9)

        self.fail("futuristic timeouts")

if __name__ == '__main__':
    logger = logging.getLogger('mikep.ex')
    #logger.setLevel(logging.DEBUG)
    #logger.addHandler(logging.StreamHandler())

    unittest.main()
