/*
 * pthread_compat.c - stub implementations for missing pthread functions
 *
 * HarmonyOS musl libc does not implement pthread_cancel and related functions.
 * This file provides stub implementations that do nothing, allowing
 * software that depends on these functions to compile and run.
 */

#include <pthread.h>
#include <errno.h>

/* Stub implementation for pthread_setcancelstate */
int pthread_setcancelstate(int state, int *oldstate)
{
    /* HarmonyOS doesn't support thread cancellation, so we just return success */
    if (oldstate) {
        *oldstate = PTHREAD_CANCEL_ENABLE;  /* pretend we're always enabled */
    }
    return 0;
}

/* Stub implementation for pthread_cancel */
int pthread_cancel(pthread_t thread)
{
    /* HarmonyOS doesn't support thread cancellation */
    /* Return ESRCH to indicate thread cannot be canceled */
    return ESRCH;
}

/* Stub implementation for pthread_setcanceltype if needed */
int pthread_setcanceltype(int type, int *oldtype)
{
    if (oldtype) {
        *oldtype = PTHREAD_CANCEL_DEFERRED;
    }
    return 0;
}