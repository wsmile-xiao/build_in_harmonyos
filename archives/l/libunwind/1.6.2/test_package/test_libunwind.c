#include <libunwind.h>

#include <stdio.h>

#if defined(__GNUC__) || defined(__clang__)
#define NOINLINE __attribute__((noinline))
#else
#define NOINLINE
#endif

static int walk_stack(void)
{
    unw_context_t context;
    unw_cursor_t cursor;
    int step_status = 0;
    int frames = 0;

    if (unw_getcontext(&context) < 0) {
        return 10;
    }
    if (unw_init_local(&cursor, &context) < 0) {
        return 11;
    }

    do {
        unw_word_t ip = 0;
        unw_word_t sp = 0;

        if (unw_get_reg(&cursor, UNW_REG_IP, &ip) < 0) {
            return 20;
        }
        if (unw_get_reg(&cursor, UNW_REG_SP, &sp) < 0) {
            return 21;
        }
        if (ip == 0 || sp == 0) {
            return 22;
        }

        frames++;
        step_status = unw_step(&cursor);
    } while (step_status > 0 && frames < 64);

    if (step_status < 0) {
        return 30;
    }
    if (frames < 1) {
        return 31;
    }

    printf("libunwind walked %d frame(s)\n", frames);
    return 0;
}

static NOINLINE int call_leaf(void)
{
    return walk_stack();
}

static NOINLINE int call_middle(void)
{
    return call_leaf();
}

int main(void)
{
    return call_middle();
}
