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
        # perhaps *always* write to a file and then raise if the file is too big to return as a string
        #  problem: stupid for known-small-output
        #   solution: caller promises short input: ex(0, cmd, expect_short_input=True)
        #      problem: what is "short"?  imprecise...
        #   solution: caller promises long input: ex(0, cmd, expect_long_input=True)
        #      problem: imprecise again...

        # NOTE: tested this on macos and linux up to 1GB without problems (aside from slowness)
        megabytes = 1
        r, out = ex(0, self.RANDOM_MEGABYTES_OF_STDOUT_CMD.format(megabytes))
        self.assertEqual(len(out), 1024 * 1024 * megabytes)

    def test_timeout(self):
        with timed(self.timer):
            r, out = ex(2, "sleep 8")

        self.assertEqual(2, self.timer.elapsed.seconds)

    def test_timeout_output(self):
        with timed(self.timer):
            r, out = ex(2, 'echo "hello world" ; sleep 4')

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

    @unittest.skip("niy")
    def test_memory_output_buffer(self):
        # opt-in to using a pipe instead of a temp file for output buffer.
        #   test stderr
        #   test timeout
        #     exits in time
        #     returns output
        # verify (how?) no file created
        #
        self.fail("niy")

    @unittest.skip("niy")
    def test_killing_of_child_processes(self):
        self.fail("niy")

    @unittest.skip("niy")
    def test_that_killer_exits(self):
        # 1) after killing the timed-out process
        # 2) if the process completes before timeout
        self.fail("niy")

    @unittest.skip("niy")
    def test_output_buffering(self):
        # make sure lines arrive in a timely manner # note: what does this even mean?  and what about osokine's complaint:
        #  if he's calling out = Ex("long process") ; print out ; long process will have to complete before output is ready.  what else?
        self.fail("niy")

    @unittest.skip("niy")
    def test_unsafe_input(self):
        # When using shell=True, pipes.quote() can be used to properly escape whitespace and shell
        #  metacharacters in strings that are going to be used to construct shell commands.
        cmd = "rm -rf /something/important"
        self.fail("niy")


if __name__ == '__main__':
    # logger = logging.getLogger('mikep.ex')
    # logger.setLevel(logging.DEBUG)
    # logger.addHandler(logging.StreamHandler())

    unittest.main()