/*
 * pthread_compat.c
 *
 * libc implementations based on a musl-like model (e.g. the OHOS SDK libc)
 * omit the thread-cancellation APIs. libkqueue references them, so provide
 * minimal no-op implementations that are marked weak: on platforms where a
 * real implementation exists (glibc etc.) the strong symbol from libc is
 * used instead, so no duplicate-definition clash can occur.
 */
#include <pthread.h>

__attribute__((weak)) int pthread_setcancelstate(int state, int* oldstate) {
    (void)state;
    if ( oldstate )
        *oldstate = PTHREAD_CANCEL_ENABLE;

    return 0;
}

__attribute__((weak)) int pthread_testcancel(void) { return 0; }

__attribute__((weak)) int pthread_cancel(pthread_t thread) {
    (void)thread;
    return 0;
}
