/* test_npth_ohos.c — npth 1.8.1 鸿蒙特有测试（OHOS arm64 / musl）
 *
 * 该测试不是上游测试的复述，而是针对本次适配中真实产生的 OHOS 平台差异点做验证：
 *   1. 编译期平台前提：目标为 OHOS（__OHOS__）且 libc 为 musl（无 __GLIBC__）——
 *      这是补丁 0003（linux-ohos 下改用 pthread_create 探测）存在的前提；
 *   2. musl 不提供 glibc 扩展 pthread_tryjoin_np（dlsym 实测为 NULL），
 *      因此本平台安装的 npth.h 不导出 tryjoin/timedjoin 系列 API，
 *      npth_join 走 npth 内部实现路径而非 glibc 扩展；
 *   3. 补丁成果回归：在 OHOS musl 上 npth 线程真实调度——
 *      子线程通过 npth_usleep（musl clock_nanosleep 路径）自旋计数，
 *      主线程 npth_join 回收并断言计数生效，npth_protect/unprotect 语义正常。
 */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

#include <npth.h>

/* ---- 1. 编译期平台前提（OHOS 三元组 + musl） ---- */
static int check_platform_macros(void)
{
#ifdef __OHOS__
    /* OK: OHOS 目标（aarch64-unknown-linux-ohos） */
#else
    fprintf(stderr, "ohos-test: __OHOS__ not defined (not an OHOS target)\n");
    return 1;
#endif

#ifdef __GLIBC__
    fprintf(stderr, "ohos-test: __GLIBC__ defined (glibc, not the adapted musl env)\n");
    return 2;
#endif
    printf("ohos-test: platform macros OK (__OHOS__ defined, musl libc)\n");
    return 0;
}

/* ---- 2. musl 无 glibc 线程扩展 pthread_tryjoin_np ---- */
static int check_musl_pthread_extensions(void)
{
    void *sym;

    dlerror();
    sym = dlsym(RTLD_DEFAULT, "pthread_tryjoin_np");
    if (sym != NULL) {
        fprintf(stderr, "ohos-test: pthread_tryjoin_np unexpectedly present (glibc?)\n");
        return 1;
    }
    printf("ohos-test: pthread_tryjoin_np absent on musl (npth uses its own join path)\n");
    return 0;
}

/* ---- 3. npth 线程在 OHOS musl 上真实调度（0003 补丁成果回归） ---- */
static volatile int worker_ticks = 0;
static volatile int worker_done = 0;
static int worker_done_marker = 42;

static void *worker_func(void *arg)
{
    int i;
    (void)arg;
    /* npth_usleep 走 musl 的 clock_nanosleep 等待路径，
     * 让出调度权，验证 OHOS 上线程挂起/唤醒真实可用 */
    for (i = 0; i < 5; i++) {
        npth_usleep(1000);
        worker_ticks++;
    }
    worker_done = 1;
    return &worker_done_marker;
}

static int check_thread_scheduling(void)
{
    npth_t tid;
    void *retval = NULL;
    int err;

    /* npth_init 后主线程持有 sceptre（保护态，源码 got_sceptre=1），
     * unprotect/protect 往返后应恢复 */
    npth_unprotect();
    npth_protect();
    if (!npth_is_protected()) {
        fprintf(stderr, "ohos-test: npth main thread should be protected after init\n");
        return 1;
    }

    err = npth_create(&tid, NULL, worker_func, NULL);
    if (err) {
        fprintf(stderr, "ohos-test: npth_create failed: %d\n", err);
        return 2;
    }
    err = npth_setname_np(tid, "ohos-worker");
    if (err) {
        fprintf(stderr, "ohos-test: npth_setname_np failed: %d\n", err);
        return 3;
    }
    err = npth_join(tid, &retval);
    if (err) {
        fprintf(stderr, "ohos-test: npth_join failed: %d\n", err);
        return 4;
    }
    if (retval != (void *)&worker_done_marker) {
        fprintf(stderr, "ohos-test: unexpected thread return value\n");
        return 5;
    }
    if (!worker_done || worker_ticks != 5) {
        fprintf(stderr, "ohos-test: worker ticks=%d done=%d (expected 5/1)\n",
                worker_ticks, worker_done);
        return 6;
    }
    printf("ohos-test: npth thread scheduling on OHOS musl OK "
           "(create+setname+usleep+join, ticks=%d)\n", worker_ticks);
    return 0;
}

int main(void)
{
    int rc;

    rc = check_platform_macros();
    if (rc)
        return rc;

    rc = check_musl_pthread_extensions();
    if (rc)
        return rc;

    if (npth_init()) {
        fprintf(stderr, "ohos-test: npth_init failed\n");
        return 10;
    }

    rc = check_thread_scheduling();
    if (rc)
        return rc;

    printf("npth 1.8.1 OHOS-specific test: ALL PASSED\n");
    return 0;
}
