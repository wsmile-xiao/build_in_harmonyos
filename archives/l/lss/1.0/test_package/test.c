/* test_package/test.c — R34: must actually include and use lss */
#include "linux_syscall_support.h"
#include <stdio.h>

int main(void) {
    /* Test 1: sys_getpid() should return a positive PID */
    long pid = sys_getpid();
    if (pid <= 0) {
        fprintf(stderr, "FAIL: sys_getpid returned %ld\n", pid);
        return 1;
    }
    printf("PASS: sys_getpid() = %ld\n", pid);

    /* Test 2: sys_close() with invalid fd should return -1 (EBADF) */
    long ret = sys_close(-1);
    if (ret != -1) {
        fprintf(stderr, "FAIL: sys_close(-1) returned %ld (expected -1)\n", ret);
        return 1;
    }
    printf("PASS: sys_close(-1) = %ld (expected -1)\n", ret);

    printf("All lss tests passed!\n");
    return 0;
}
