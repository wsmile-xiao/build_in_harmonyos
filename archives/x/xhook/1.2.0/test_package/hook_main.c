/* Mirrors upstream libbiz/jni/biz.c + the xhookwrapper demo app: the hook
 * consumer. Registers an xhook for malloc in the dlopen'ed victim library,
 * refreshes (synchronously so old_func is written before we read it), and verifies:
 *   1. the hook replacement function is actually invoked (PLT/GOT patched),
 *   2. calls keep flowing over time (before < after),
 *   3. old_func captured the original malloc address from the GOT.
 * Exits 0 only when the PLT hook demonstrably works on the running system.
 */
#include <dlfcn.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "xhook.h"

static volatile int hook_calls = 0;
static pthread_mutex_t cnt_mutex = PTHREAD_MUTEX_INITIALIZER;

static void *my_malloc(size_t size)
{
    void *r;
    pthread_mutex_lock(&cnt_mutex);
    hook_calls++;
    pthread_mutex_unlock(&cnt_mutex);
    r = calloc(1, size ? size : 1); /* different PLT slot, not hooked */
    return r;
}

int main(void)
{
    int before, after, rc = 0;
    void *old = (void *)1;
    void *h = dlopen("./libhooktarget.so", RTLD_NOW);

    if(NULL == h)
    {
        printf("FAIL: dlopen: %s\n", dlerror());
        return 1;
    }
    void (*start)(void) = (void (*)(void))dlsym(h, "target_start");
    if(NULL == start)
    {
        printf("FAIL: dlsym target_start\n");
        return 1;
    }

    if(0 != xhook_register(".*/libhooktarget\\.so$", "malloc",
                           (void *)my_malloc, &old))
    {
        printf("FAIL: xhook_register\n");
        return 1;
    }
    /* synchronous refresh so old_func is populated by the time we check */
    if(0 != xhook_refresh(0))
    {
        printf("FAIL: xhook_refresh\n");
        return 1;
    }
    if(old == (void *)1 || old == NULL)
    {
        printf("FAIL: old_func not captured\n");
        rc = 1;
    }

    start();
    sleep(3);
    pthread_mutex_lock(&cnt_mutex);
    before = hook_calls;
    pthread_mutex_unlock(&cnt_mutex);
    sleep(2);
    pthread_mutex_lock(&cnt_mutex);
    after = hook_calls;
    pthread_mutex_unlock(&cnt_mutex);

    printf("hook_calls: before=%d after=%d old_func=%p\n", before, after, old);
    if(before < 1 || after <= before)
    {
        printf("FAIL: PLT hook not firing\n");
        rc = 1;
    }
    else
    {
        printf("PASS: PLT hook is active and firing\n");
    }

    xhook_clear();
    return rc;
}
