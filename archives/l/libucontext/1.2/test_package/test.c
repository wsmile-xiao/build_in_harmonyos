/*
 * libucontext test program based on POSIX example program.
 * Public domain.
 */

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <libucontext/libucontext.h>

static libucontext_ucontext_t ctx[3];

static void check_result(int result, const char *operation)
{
    if (result == 0)
        return;
    perror(operation);
    abort();
}

static void check_arg(int actual, int expected)
{
    if (actual == expected)
        return;
    fprintf(stderr, "argument has wrong value. got %d, expected %d.\n",
            actual, expected);
    abort();
}

static void f1(int a, int b, int c, int d, int e,
               int f, int g, int h, int i, int j)
{
    puts("start f1");
    puts("checking provided arguments to function f1");
    check_arg(a, 1);
    check_arg(b, 2);
    check_arg(c, 3);
    check_arg(d, 4);
    check_arg(e, 5);
    check_arg(f, 6);
    check_arg(g, 7);
    check_arg(h, 8);
    check_arg(i, 9);
    check_arg(j, 10);
    puts("looks like all arguments are passed correctly");

    puts("swap back to f2");
    check_result(libucontext_swapcontext(&ctx[1], &ctx[2]),
                 "libucontext_swapcontext(f1->f2)");
    puts("finish f1");
}

static void f2(void)
{
    puts("start f2");
    puts("swap to f1");
    check_result(libucontext_swapcontext(&ctx[2], &ctx[1]),
                 "libucontext_swapcontext(f2->f1)");
    puts("finish f2, should swap to f1");
}

int main(void)
{
    char st1[8192];
    char st2[8192];
    volatile int done = 0;

    memset(st1, 'A', sizeof(st1));
    memset(st2, 'B', sizeof(st2));

    puts("setting up context 1");
    check_result(libucontext_getcontext(&ctx[1]),
                 "libucontext_getcontext(ctx1)");
    ctx[1].uc_stack.ss_sp = st1;
    ctx[1].uc_stack.ss_size = sizeof(st1);
    ctx[1].uc_link = &ctx[0];
    libucontext_makecontext(&ctx[1], f1, 10,
                            1, 2, 3, 4, 5, 6, 7, 8, 9, 10);

    puts("setting up context 2");
    check_result(libucontext_getcontext(&ctx[2]),
                 "libucontext_getcontext(ctx2)");
    ctx[2].uc_stack.ss_sp = st2;
    ctx[2].uc_stack.ss_size = sizeof(st2);
    ctx[2].uc_link = &ctx[1];
    libucontext_makecontext(&ctx[2], f2, 0);

    puts("doing initial swapcontext");
    check_result(libucontext_swapcontext(&ctx[0], &ctx[2]),
                 "libucontext_swapcontext(main->f2)");
    puts("returned from initial swapcontext");

    check_result(libucontext_getcontext(&ctx[1]),
                 "libucontext_getcontext(roundtrip)");
    printf("done = %d\n", done);
    if (done++ == 0)
        check_result(libucontext_setcontext(&ctx[1]),
                     "libucontext_setcontext(roundtrip)");
    if (done != 2) {
        fprintf(stderr, "wrong value for done. got %d, expected 2\n", done);
        abort();
    }

    return 0;
}
