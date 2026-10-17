/* test_debugbreak — real consumer test of the debugbreak API on OHOS.
 *
 * debug_break() compiles to the aarch64 breakpoint instruction
 * (.inst 0xd4200000, brk #0), which raises SIGTRAP. A SIGTRAP handler is
 * installed; if debug_break() actually traps, control returns via longjmp
 * and the test passes. This proves the header's inline assembly is live
 * on the OHOS aarch64 toolchain rather than falling back to a no-op.
 */
#include <setjmp.h>
#include <signal.h>
#include <stdio.h>

#include "debugbreak.h"

static volatile int trap_fired = 0;
static jmp_buf jmp_env;

static void on_sigtrap(int sig) {
    (void)sig;
    trap_fired = 1;
    longjmp(jmp_env, 1);
}

int main(void) {
    struct sigaction sa = {0};
    sa.sa_handler = on_sigtrap;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = 0;
    if (sigaction(SIGTRAP, &sa, NULL) != 0) {
        perror("sigaction");
        return 1;
    }

    if (setjmp(jmp_env) == 0) {
        debug_break();   /* must raise SIGTRAP and longjmp back */
        printf("FAIL: debug_break() returned without trapping\n");
        return 1;
    }
    if (!trap_fired) {
        printf("FAIL: SIGTRAP handler was not invoked\n");
        return 1;
    }
    printf("PASS: debug_break() raised SIGTRAP on OHOS aarch64\n");
    return 0;
}
