/*
 * pthread_stubs.c — stubs for unimplemented pthread functions on OHOS.
 *
 * OHOS bionic libc does not implement pthread_cancel() or
 * pthread_setcancelstate() (E051). libfuse's multithreaded loop
 * (fuse_loop_mt.c) references these symbols. Since FUSE cannot mount
 * on OHOS without a kernel module, these stubs allow the test binary
 * to link. If the multithreaded loop is actually invoked, the stubs
 * return -1 (ENOSYS semantics).
 */
#include <pthread.h>
#include <errno.h>

/* weak stub so the linker resolves the symbol; returns error if called */
int pthread_cancel(pthread_t thread)
{
    (void)thread;
    errno = ENOSYS;
    return -1;
}

int pthread_setcancelstate(int state, int *oldstate)
{
    if (oldstate)
        *oldstate = PTHREAD_CANCEL_ENABLE;
    (void)state;
    errno = ENOSYS;
    return -1;
}
