/* test.c — libsigsegv 2.14 实质性测试 (R34)
 * 验证被测包核心 API（用法参照上游 tests/test-catch-segv2.c / test-catch-stackoverflow1.c）：
 *   1. sigsegv_install_handler() 安装 SIGSEGV 处理器，
 *      空指针解引用触发 SIGSEGV，经 sigsegv_leave_handler(continuation,...) + longjmp 恢复
 *   2. stackoverflow_install_handler() 安装栈溢出处理器（sigaltstack 路径），
 *      无限递归触发栈溢出，捕获后 longjmp 逃逸恢复
 *   3. stackoverflow_deinstall_handler() / sigsegv_deinstall_handler() 卸载
 *   4. libsigsegv_version 校验为 2.14 (0x020E)
 */
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <setjmp.h>
#include <sys/types.h>
#include <sys/time.h>
#include <sys/resource.h>
#include <sigsegv.h>

#ifndef SIGSTKSZ
# define SIGSTKSZ 16384
#endif
/* 参照上游 altstack-util.h：备用栈两端各留 8KB crumple zone，防止 handler 内
 * printf 等调用在备用栈上二次溢出（OHOS musl 信号处理器在 sigaltstack 上运行）。 */
#define MYSTACK_CRUMPLE_ZONE 8192
static unsigned long mystack_storage[(SIGSTKSZ + 2 * MYSTACK_CRUMPLE_ZONE + 31)
                                      / sizeof(unsigned long)];
static unsigned long *mystack;

static jmp_buf mainloop;
static sigset_t mainsigset;

static volatile int segv_pass = 0;
static volatile int so_pass = 0;

/* --- SIGSEGV（空指针解引用）测试 --- */

static void segv_continuation(void *arg1, void *arg2, void *arg3)
{
    (void) arg2;
    (void) arg3;
    longjmp(mainloop, (int) (long) arg1);
}

static int segv_handler(void *fault_address, int serious)
{
    (void) fault_address;
    (void) serious;
    segv_pass++;
    /* 恢复信号掩码后经 continuation 逃逸 */
    sigprocmask(SIG_SETMASK, &mainsigset, NULL);
    return sigsegv_leave_handler(segv_continuation,
                                 (void *) (long) segv_pass, NULL, NULL);
}

/* --- 栈溢出测试（参照上游 stackoverflow_handler 写法）--- */

static void so_continuation(void *arg1, void *arg2, void *arg3)
{
    (void) arg2;
    (void) arg3;
    longjmp(mainloop, (int) (long) arg1);
}

static void stackoverflow_handler(int emergency, stackoverflow_context_t scp)
{
    (void) emergency;
    (void) scp;
    so_pass++;
    sigprocmask(SIG_SETMASK, &mainsigset, NULL);
    sigsegv_leave_handler(so_continuation,
                          (void *) (long) so_pass, NULL, NULL);
}

static int recurse(volatile int n)
{
    volatile char pad[4096];
    pad[0] = (char) n;
    return recurse(n + 1) + pad[0];
}

int main(void)
{
    sigset_t emptyset;
#if defined(RLIMIT_STACK)
    /* 参照上游 test-catch-stackoverflow1.c：先限制主栈为 1MB。
     * OHOS musl 默认无栈限制时，无限递归会一次越过 guard page 过深，
     * SIGSEGV 故障地址远离栈区，无法被识别为栈溢出，恢复失败。 */
    struct rlimit rl;
    rl.rlim_cur = rl.rlim_max = 0x100000;
    setrlimit(RLIMIT_STACK, &rl);
#endif

    /* 准备备用栈：SIGSTKSZ 居中，两端 crumple zone */
    mystack = (unsigned long *)
        (((uintptr_t) mystack_storage + MYSTACK_CRUMPLE_ZONE) & ~(uintptr_t) 31);

    sigemptyset(&emptyset);
    sigprocmask(SIG_BLOCK, &emptyset, &mainsigset);

    /* --- Test 1: sigsegv_install_handler + SIGSEGV 捕获恢复 --- */
    if (sigsegv_install_handler(segv_handler) < 0) {
        printf("FAIL: sigsegv_install_handler not supported\n");
        return 1;
    }
    if (setjmp(mainloop) == 0) {
        volatile int *p = (volatile int *) 0;
        *p = 42; /* 触发 SIGSEGV */
        printf("FAIL: null deref returned without fault\n");
        return 1;
    }
    if (segv_pass != 1) {
        printf("FAIL: segv handler pass=%d (expected 1)\n", (int) segv_pass);
        return 1;
    }
    printf("PASS: SIGSEGV caught via sigsegv_install_handler\n");
    sigsegv_deinstall_handler();

    /* --- Test 2: stackoverflow_install_handler + 栈溢出捕获恢复 --- */
    if (stackoverflow_install_handler(stackoverflow_handler,
                                      (void *) mystack, SIGSTKSZ) < 0) {
        printf("FAIL: stackoverflow_install_handler not supported\n");
        return 1;
    }
    if (setjmp(mainloop) == 0) {
        recurse(0); /* 无限递归触发栈溢出 */
        printf("FAIL: recursion returned without overflow\n");
        return 1;
    }
    if (so_pass < 1) {
        printf("FAIL: stack overflow handler never invoked\n");
        return 1;
    }
    printf("PASS: stack overflow caught via stackoverflow_install_handler\n");
    stackoverflow_deinstall_handler();

    /* --- Test 3: 版本标识 --- */
    if (libsigsegv_version != 0x020E) {
        printf("FAIL: libsigsegv_version=0x%x (expected 0x2000e)\n",
               libsigsegv_version);
        return 1;
    }
    printf("PASS: libsigsegv_version = 2.14\n");

    printf("ALL TESTS PASSED\n");
    return 0;
}
