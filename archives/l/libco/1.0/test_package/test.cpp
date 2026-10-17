#include <stdio.h>
#include <assert.h>
#include "co_routine.h"

// Real consumer test (R34): exercises co_create/co_resume/co_yield_ct,
// which drives coctx_make + the aarch64 coctx_swap assembly.
static int g_counter = 0;

static void *co_func(void *arg) {
    (void)arg;
    for (int i = 0; i < 100; i++) {
        g_counter++;
        co_yield_ct();
    }
    return NULL;
}

int main(void) {
    stCoRoutine_t *co = NULL;
    int ret = co_create(&co, NULL, co_func, NULL);
    assert(ret == 0);
    for (int i = 0; i < 100; ++i) {
        co_resume(co);
    }
    assert(g_counter == 100);
    printf("libco 1.0 coroutine yield/resume test: OK (counter=%d)\n", g_counter);
    return 0;
}
