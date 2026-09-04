#ifndef __OHOS__
#error "test_ohos_ucontext must only be built for OHOS"
#endif

#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <ucontext.h>

/*
 * OHOS exposes ucontext_t in <ucontext.h>, but does not declare the legacy
 * context functions. These declarations name the unprefixed ABI supplied by
 * libucontext/libucontext_posix rather than the prefixed consumer API.
 */
int getcontext(ucontext_t *context);
void makecontext(ucontext_t *context, void (*function)(void), int argc, ...);
int setcontext(const ucontext_t *context);
int swapcontext(ucontext_t *old_context, const ucontext_t *new_context);

static ucontext_t main_context;
static ucontext_t child_context;
static unsigned char child_stack[16384];
static volatile sig_atomic_t child_ran;
static int failures;
static int original_sigusr1_blocked;

static void fail(const char *message)
{
    fprintf(stderr, "FAIL: %s\n", message);
    failures++;
}

static int is_blocked(int signal_number)
{
    sigset_t current;
    if (sigprocmask(SIG_SETMASK, NULL, &current) != 0) {
        perror("sigprocmask(query)");
        exit(2);
    }
    return sigismember(&current, signal_number) == 1;
}

static void child_entry(int a1, int a2, int a3, int a4, int a5,
                        int a6, int a7, int a8, int a9, int a10)
{
    const int values[10] = {a1, a2, a3, a4, a5, a6, a7, a8, a9, a10};
    int index;

    for (index = 0; index < 10; ++index) {
        if (values[index] != index + 1) {
            fail("makecontext argument transfer");
            break;
        }
    }
    if (!is_blocked(SIGUSR1))
        fail("child signal mask was not restored");
#if defined(__aarch64__)
    {
        uintptr_t stack_pointer;
        __asm__ volatile("mov %0, sp" : "=r"(stack_pointer));
        if ((stack_pointer & 15U) != 0)
            fail("aarch64 stack pointer is not 16-byte aligned");
    }
#endif
    child_ran = 1;
    if (swapcontext(&child_context, &main_context) != 0) {
        perror("swapcontext(child->main)");
        exit(2);
    }
}

int main(void)
{
    sigset_t original;
    sigset_t child_mask;

    if (sigprocmask(SIG_SETMASK, NULL, &original) != 0) {
        perror("sigprocmask(original)");
        return 2;
    }
    original_sigusr1_blocked = sigismember(&original, SIGUSR1) == 1;
    child_mask = original;
    if (sigaddset(&child_mask, SIGUSR1) != 0 ||
        sigprocmask(SIG_SETMASK, &child_mask, NULL) != 0) {
        perror("sigprocmask(block child)");
        return 2;
    }
    if (getcontext(&child_context) != 0) {
        perror("getcontext(child)");
        return 2;
    }
    child_context.uc_stack.ss_sp = child_stack;
    child_context.uc_stack.ss_size = sizeof(child_stack);
    child_context.uc_link = NULL;
    makecontext(&child_context, (void (*)(void))child_entry, 10,
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10);
    if (sigprocmask(SIG_SETMASK, &original, NULL) != 0) {
        perror("sigprocmask(restore before switch)");
        return 2;
    }
    if (swapcontext(&main_context, &child_context) != 0) {
        perror("swapcontext(main->child)");
        return 2;
    }
    if (!child_ran)
        fail("child context did not run");
    if (is_blocked(SIGUSR1) != original_sigusr1_blocked)
        fail("main signal mask was not restored");
    if (sigprocmask(SIG_SETMASK, &original, NULL) != 0) {
        perror("sigprocmask(final restore)");
        return 2;
    }
    if (failures != 0)
        return 1;
    puts("OHOS ucontext compatibility: PASS");
    return 0;
}
