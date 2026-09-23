/* Mirrors upstream libtest/jni/test.c (xhook v1.2.0): the "victim" library.
 *
 * Upstream's libtest spawns a thread that calls __android_log_print through
 * three different code paths (direct call, global pointer, local pointer) so
 * the demo app can show xhook redirecting them. On OHOS the equivalent
 * always-available PLT symbol is malloc, so this port calls malloc/free in a
 * loop from a background thread: every call goes through the library's PLT
 * exactly like the upstream log calls.
 */
#include <pthread.h>
#include <stdlib.h>
#include <unistd.h>

static void *new_thread_func(void *arg)
{
    (void)arg;
    while(1)
    {
        /* volatile sink: keeps the PLT malloc/free calls alive under -O
         * (dead-code elimination would otherwise drop the entire loop body
         * since upstream's demo relies on the log side effect instead) */
        static volatile unsigned char *sink;
        void *p = malloc(16);
        if(NULL != p) sink = (unsigned char *)p;
        free(p);
        sleep(1);
    }
    return NULL;
}

__attribute__((visibility("default")))
void target_start(void)
{
    pthread_t tid;
    pthread_create(&tid, NULL, &new_thread_func, NULL);
}
