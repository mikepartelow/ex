import unittest
import time
from Ex import ex

class ExTest(unittest.TestCase):
    RANDOM_MEGABYTES_OF_STDOUT_CMD = "dd if=/dev/random of=/dev/stdout bs=1048576 count={} 2>/dev/null"

    def setUp(self):
        pass

    def tearDown(self):
        pass

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

    def test_unsafe_input(self):
        cmd = "rm -rf /something/important"
        self.fail("niy")

    def test_large_output(self):
        # perhaps *always* write to a file and then raise if the file is too big to return as a string
        #  problem: stupid for known-small-output
        #   solution: caller promises short input: ex(0, cmd, expect_short_input=True)
        #      problem: what is "short"?  imprecise...
        #   solution: caller promises long input: ex(0, cmd, expect_long_input=True)
        #      problem: imprecise again...

        # NOTE: tested this on macos up to 1GB and it had no problems...
        megabytes = 8
        r, out = ex(0, self.RANDOM_MEGABYTES_OF_STDOUT_CMD.format(megabytes))
        self.assertEqual(len(out), 1024 * 1024 * megabytes)

    def test_output_buffering(self):
        # make sure lines arrive in a timely manner # note: what does this even mean?  and what about osokine's complaint:
        #  if he's calling out = Ex("long process") ; print out ; long process will have to complete before output is ready.  what else?
        self.fail("niy")

if __name__ == '__main__':
    unittest.main()
