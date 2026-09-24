/* libmill consumer test.
 *
 * Links the installed libmill and exercises the two things the library exists
 * for — coroutines and channels — through the real public API in <libmill.h>
 * (R34: the test must drive the package under test, not merely link it).
 *
 * The idioms are the ones upstream's own tests/chan.c and tests/go.c use:
 * a coroutine receives a duplicated channel reference (chdup) because the
 * channel is reference-counted, and the main coroutine is itself a coroutine
 * as far as the scheduler is concerned.
 */

#include <libmill.h>

#include <stdio.h>

static int failures = 0;

static void check(int ok, const char *what)
{
    printf("%s %s\n", ok ? "ok  " : "FAIL", what);
    if (!ok) {
        ++failures;
    }
}

/* Accumulates into a file-scope variable, yielding after every step so the
 * scheduler has to interleave the coroutine with main. */
static int total = 0;

coroutine void accumulator(int times, int step)
{
    int i;
    for (i = 0; i != times; ++i) {
        total += step;
        yield();
    }
}

coroutine void sender(chan ch, int value)
{
    chs(ch, int, value);
    chclose(ch);
}

int main(void)
{
    int val;
    int64_t before, after;

    goprepare(8, 25000, 300);

    /* 1. coroutines actually run and yield: 6 rounds of +7 must give 42 */
    total = 0;
    go(accumulator(6, 7));
    msleep(now() + 100);
    check(total == 42, "coroutine ran to completion (6 x +7 == 42)");

    /* 2. a value travels from a coroutine to main over an unbuffered channel */
    {
        chan ch = chmake(int, 0);
        go(sender(chdup(ch), 333));
        val = chr(ch, int);
        check(val == 333, "unbuffered channel delivered 333");
        chclose(ch);
    }

    /* 3. two simultaneous senders are delivered in order */
    {
        chan ch = chmake(int, 0);
        go(sender(chdup(ch), 888));
        go(sender(chdup(ch), 999));
        val = chr(ch, int);
        check(val == 888, "first of two senders delivered 888");
        yield();
        val = chr(ch, int);
        check(val == 999, "second of two senders delivered 999");
        chclose(ch);
    }

    /* 4. a buffered channel accepts a send with no receiver waiting */
    {
        chan ch = chmake(int, 1);
        chs(ch, int, 1);
        val = chr(ch, int);
        check(val == 1, "buffered channel round-tripped 1");
        chclose(ch);
    }

    /* 5. time advances across msleep */
    {
        before = now();
        msleep(before + 50);
        after = now();
        check(after >= before + 50, "msleep advanced the clock by at least 50ms");
    }

    if (failures != 0) {
        fprintf(stderr, "%d libmill consumer check(s) FAILED\n", failures);
        return 1;
    }
    printf("all libmill consumer checks passed\n");
    return 0;
}
