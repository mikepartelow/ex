import sys, multiprocessing, time, os, shutil

def start_children(child_count, pid_dir):
    children = []

    for i in xrange(0, child_count):
        print " starting child {}".format(i)
        child = multiprocessing.Process(target=do_the_child_thing, args=(child_count, pid_dir,))
        children.append(child)
        child.start()

    return children

def do_the_child_thing(child_count, pid_dir):
    my_pid = os.getpid()

    print "  my pid: {}".format(my_pid)

    with open(os.path.join(pid_dir, str(my_pid)), 'w') as f:
        f.write(str(my_pid))

    children = start_children(child_count - 1, pid_dir)
    map(lambda c: c.join(), children)

    while True:
        time.sleep(60)

if __name__ == "__main__":
    child_count     = int(sys.argv[1])
    pid_dir         = sys.argv[2]

    print " top level pid: {}".format(os.getpid())

    shutil.rmtree(pid_dir, ignore_errors=True)
    try:
        os.makedirs(pid_dir)
    except OSError:
        pass

    children = start_children(child_count, pid_dir)
    map(lambda c: c.join(), children)