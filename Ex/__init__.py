# FIXME:
# See also POSIX users (Linux, BSD, etc.) are strongly encouraged to install and use the much more recent subprocess32 module
# instead of the version included with python 2.7. It is a drop in replacement with better behavior in many situations.

import subprocess

def ex(timeout_seconds, command):
    # FIXME: When using shell=True, pipes.quote() can be used to properly escape whitespace and shell metacharacters in
    #        strings that are going to be used to construct shell commands.
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    output = p.stdout.read()
    exit_code = p.wait()
    return exit_code, output