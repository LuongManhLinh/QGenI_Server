thread_continous_flags = {}

def is_thread_stopped(addr):
    flag = thread_continous_flags[addr]
    return flag is None or not flag