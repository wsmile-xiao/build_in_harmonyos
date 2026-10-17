// test_package consumer test for libaco 1.2.2 (HarmonyOS / aarch64)
// Actually exercises the installed libaco API: share-stack lifecycle,
// coroutine create/resume/yield/exit, arg passing and main-co return.
#include <stdio.h>
#include <aco.h>

static int g_yield_ct;
static int g_bad;

static void co_fp(void) {
    aco_t* co = aco_get_co();
    if (co->arg != (void*)0x7c0ffee) {
        g_bad = 1;
        fprintf(stderr, "libaco consumer test: arg mismatch\n");
        aco_exit();
    }
    while (g_yield_ct < 3) {
        g_yield_ct++;
        aco_yield();
    }
    aco_exit();
}

int main(void) {
    aco_thread_init(NULL);
    aco_runtime_test();

    aco_share_stack_t* sstk = aco_share_stack_new(0);
    if (!sstk) {
        fprintf(stderr, "libaco consumer test: share_stack_new failed\n");
        return 1;
    }
    aco_t* main_co = aco_create(NULL, NULL, 0, NULL, NULL);
    if (!main_co) {
        fprintf(stderr, "libaco consumer test: main_co create failed\n");
        return 1;
    }
    aco_t* co = aco_create(main_co, sstk, 0, co_fp, (void*)0x7c0ffee);
    if (!co) {
        fprintf(stderr, "libaco consumer test: co create failed\n");
        return 1;
    }
    g_yield_ct = 0;
    g_bad = 0;
    while (g_yield_ct < 3 && !g_bad) {
        aco_resume(co);
    }
    if (g_yield_ct != 3 || g_bad) {
        fprintf(stderr, "libaco consumer test FAILED: yield_ct=%d bad=%d\n",
                g_yield_ct, g_bad);
        return 1;
    }
    aco_destroy(co);
    aco_destroy(main_co);
    aco_share_stack_destroy(sstk);

    printf("libaco consumer test PASSED (3 yields, arg preserved)\n");
    return 0;
}
