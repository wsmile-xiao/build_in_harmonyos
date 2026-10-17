/* test.c — Consumer smoke test for libexecinfo.
 *
 * Uses the library's public API (execinfo.h): records the current call stack
 * with backtrace() and prints symbols via backtrace_symbols_fd().  This is a
 * real consumer exercising the installed headers + linked library at runtime,
 * not a print-only stub (R34).
 */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <execinfo.h>

#define MAX_FRAMES 32

static int deep_call(int depth)
{
    void *frames[MAX_FRAMES];
    int n;

    /* Intentional recursion to give the unwinder several frames to walk.
     * 返回值必须透传：内层 deep_call() 在 backtrace() 失败时返回 -1，
     * 若在此无条件 return 0 会把失败吞掉，main 恒得到 0 而误报 PASS。 */
    if (depth > 0) {
        return deep_call(depth - 1);
    }

    n = backtrace(frames, MAX_FRAMES);
    if (n <= 0) {
        fprintf(stderr, "FAIL: backtrace() returned %d frames\n", n);
        return -1;
    }
    backtrace_symbols_fd(frames, n, STDOUT_FILENO);
    printf("INFO: captured %d frames\n", n);
    return 0;
}

int main(void)
{
    int rc = deep_call(3);
    if (rc != 0)
        return EXIT_FAILURE;
    printf("PASS: libexecinfo backtrace consumer ran successfully\n");
    return EXIT_SUCCESS;
}