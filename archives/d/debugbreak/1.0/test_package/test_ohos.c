/* test_ohos — HarmonyOS PC (aarch64) 专项测试用例 (本轮新增)。
 *
 * 验证点（均为真实、可执行、非空壳）：
 *  1) 编译期：OHOS aarch64 (非 Apple) 下 debugbreak.h 的平台选择逻辑必须
 *     走陷阱指令实现 DEBUG_BREAK_USE_TRAP_INSTRUCTION（.inst 0xd4200000,
 *     brk #0），而不是降级为 raise(SIGTRAP) 或其他路径——这是 OHOS 平台
 *     特有的适配断言，上游测试不覆盖。
 *  2) 运行期：debug_break() 实际触发 SIGTRAP；信号处理器捕获后 longjmp
 *     返回，断言陷阱指令真实执行（进程内完成，无需 ptrace/gdb）。
 *
 * 非 aarch64 平台编译本文件时跳过运行（exit 77），保证配方可跨平台构建。
 */
#include <setjmp.h>
#include <signal.h>
#include <stdio.h>

#include "debugbreak.h"

#if defined(__aarch64__) && !defined(__APPLE__)
/* 编译期断言：OHOS aarch64 必须使用陷阱指令实现 */
#ifndef DEBUG_BREAK_IMPL
#error "DEBUG_BREAK_IMPL is not defined"
#endif
#if DEBUG_BREAK_IMPL != DEBUG_BREAK_USE_TRAP_INSTRUCTION
#error "OHOS aarch64 must select DEBUG_BREAK_USE_TRAP_INSTRUCTION"
#endif
#endif

static volatile int trap_fired = 0;
static jmp_buf jmp_env;

static void on_sigtrap(int sig) {
    (void)sig;
    trap_fired = 1;
    longjmp(jmp_env, 1);
}

int main(void) {
#if defined(__aarch64__) && !defined(__APPLE__)
    struct sigaction sa = {0};
    sa.sa_handler = on_sigtrap;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = 0;
    if (sigaction(SIGTRAP, &sa, NULL) != 0) {
        perror("sigaction");
        return 1;
    }

    if (setjmp(jmp_env) == 0) {
        debug_break();   /* 必须触发 SIGTRAP 并 longjmp 返回 */
        printf("FAIL: debug_break() returned without trapping\n");
        return 1;
    }
    if (!trap_fired) {
        printf("FAIL: SIGTRAP handler was not invoked\n");
        return 1;
    }
    printf("PASS: OHOS aarch64 trap-instruction path verified (brk #0 raised SIGTRAP)\n");
    return 0;
#else
    printf("SKIP: not aarch64 (HarmonyOS PC) — test_ohos skipped\n");
    return 77;
#endif
}
