/*
 * test_com_err.c — consumer smoke test for libcom_err 1.47.4.
 *
 * Exercises the real com_err public API deterministically (no dependence
 * on libc errno strings, which differ between musl/glibc):
 *   1. init_error_table() registers a custom error table; it returns void,
 *      so its success is asserted via the observable side effect that
 *      error_message(base) resolves to the just-registered "reserved" entry.
 *   2. error_message(base+1) resolves table offset 1 -> "demo one"
 *   3. error_message(base+2) resolves table offset 2 -> "demo two"
 *   4. error_message(-1)     exercises com_err's own unknown-code formatter
 *   5. set_com_err_hook() + com_err() dispatches to a custom hook
 *
 * Each CHECK increments a real counter and has an explicit fail exit path.
 * On completion the program prints the HMBS_TEST_PACKAGE_RESULT marker with
 * discovered/passedCount taken straight from those counters.
 */
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <et/com_err.h>

static int checks = 0;
static int failures = 0;
static int hook_called = 0;

#define CHECK(cond, name)                                            \
    do {                                                             \
        checks++;                                                    \
        if (!(cond)) {                                               \
            fprintf(stderr, "FAIL: %s\n", name);                     \
            failures++;                                              \
        } else {                                                     \
            printf("OK: %s\n", name);                                \
        }                                                            \
    } while (0)

static void my_com_err_hook(const char *whoami, long code, const char *fmt,
                            va_list args)
{
    hook_called = 1;
    const char *m = error_message(code);
    if (m && m[0] == '\0')
        hook_called = -1;
}

int main(void)
{
    static const char *const msgs[] = { "reserved", "demo one", "demo two" };
    long base = 0x42424200L; /* distinctive non-errno table base */

    /* 1. register a table.  init_error_table() returns void (com_err.h
     *    prototype), so assert registration via the observable side effect:
     *    a successful register makes error_message(base) resolve the entry. */
    init_error_table(msgs, base, 3);
    {
        const char *m = error_message(base);
        CHECK(m != NULL && strcmp(m, "reserved") == 0,
              "init_error_table registered table");
    }

    /* 2. table lookup of offset 1 */
    {
        const char *m = error_message(base + 1);
        CHECK(m != NULL && strcmp(m, "demo one") == 0,
              "error_message table offset 1");
    }

    /* 3. table lookup of offset 2 */
    {
        const char *m = error_message(base + 2);
        CHECK(m != NULL && strcmp(m, "demo two") == 0,
              "error_message table offset 2");
    }

    /* 4. unknown (negative) code -> com_err internal formatter */
    {
        const char *m = error_message(-1L);
        CHECK(m != NULL && m[0] != '\0', "error_message unknown code");
    }

    /* 5. hook dispatch through com_err() */
    set_com_err_hook(my_com_err_hook);
    hook_called = 0;
    com_err("testprog", base, "hello %d", 42);
    CHECK(hook_called == 1, "com_err hook dispatch");
    reset_com_err_hook();

    if (failures == 0) {
        printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,"
               "\"command\":\"./test_com_err\",\"discovered\":%d,\"passedCount\":%d}\n",
               checks, checks);
        return 0;
    }
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,"
           "\"command\":\"./test_com_err\",\"discovered\":%d,\"passedCount\":%d}\n",
           checks, checks - failures);
    return 1;
}
