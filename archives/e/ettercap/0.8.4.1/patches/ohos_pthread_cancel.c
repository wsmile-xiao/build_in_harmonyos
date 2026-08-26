/*
 * OHOS platform stub for pthread cancellation functions.
 *
 * OHOS libc.so does not export pthread_cancel, pthread_testcancel,
 * pthread_setcancelstate, pthread_setcanceltype (they exist only in
 * libc.a). Since ettercap links as a static library into executables,
 * we provide these symbols here.
 *
 * Thread cancellation is implemented as a no-op: pthread_cancel returns 0
 * (success) but does not actually cancel the thread. Consequently, the
 * BROKEN_PTHREAD_JOIN macro is defined in CMakeLists.txt so that
 * ec_thread_destroy/ec_thread_kill_all skip pthread_join after the no-op
 * cancel (which would otherwise block forever on a joinable thread).
 * Threads are reaped by the runtime on process exit.
 */
#include <pthread.h>

int pthread_cancel(pthread_t thread)
{
    (void)thread;
    return 0;
}

void pthread_testcancel(void)
{
    /* No cancellation support — no-op */
}

int pthread_setcancelstate(int state, int *oldstate)
{
    if (oldstate)
        *oldstate = PTHREAD_CANCEL_ENABLE;
    (void)state;
    return 0;
}

int pthread_setcanceltype(int type, int *oldtype)
{
    if (oldtype)
        *oldtype = PTHREAD_CANCEL_DEFERRED;
    (void)type;
    return 0;
}
