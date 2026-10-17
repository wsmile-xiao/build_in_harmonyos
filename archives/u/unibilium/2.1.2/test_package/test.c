#include <unibilium.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* test_unibilium — verify the real unibilium API surface is usable (R34).
 * Exercises: object lifecycle, boolean/numeric/string capability
 * round-trips, alias handling, serialization round-trip via unibi_dump()
 * + unibi_from_mem(), and name lookup helpers. Prints TAP-style output and
 * exits 0 only when every assertion passes. */
int main(void) {
    int fails = 0;
    char buf[65536];

    unibi_term *ut = unibi_dummy();
    if (!ut) {
        printf("not ok 1 - unibi_dummy()\n");
        return 1;
    }
    printf("ok 1 - unibi_dummy()\n");

    /* Name roundtrip. */
    unibi_set_name(ut, "test-term");
    const char *name = unibi_get_name(ut);
    if (name && strcmp(name, "test-term") == 0) {
        printf("ok 2 - unibi_set_name/get_name roundtrip\n");
    } else {
        printf("not ok 2 - unibi_set_name/get_name roundtrip\n");
        fails++;
    }

    /* Boolean capability roundtrip. */
    unibi_set_bool(ut, unibi_auto_left_margin, 1);
    if (unibi_get_bool(ut, unibi_auto_left_margin) == 1) {
        printf("ok 3 - unibi_set_bool/get_bool roundtrip\n");
    } else {
        printf("not ok 3 - unibi_set_bool/get_bool roundtrip\n");
        fails++;
    }

    /* Numeric capability roundtrip. */
    unibi_set_num(ut, unibi_columns, 80);
    if (unibi_get_num(ut, unibi_columns) == 80) {
        printf("ok 4 - unibi_set_num/get_num roundtrip\n");
    } else {
        printf("not ok 4 - unibi_set_num/get_num roundtrip\n");
        fails++;
    }

    /* String capability roundtrip. */
    unibi_set_str(ut, unibi_clear_screen, "\033[H\033[J");
    const char *cs = unibi_get_str(ut, unibi_clear_screen);
    if (cs && strcmp(cs, "\033[H\033[J") == 0) {
        printf("ok 5 - unibi_set_str/get_str roundtrip\n");
    } else {
        printf("not ok 5 - unibi_set_str/get_str roundtrip\n");
        fails++;
    }

    /* Alias handling. */
    static const char *aliases[] = {"screen", "test", NULL};
    unibi_set_aliases(ut, aliases);
    const char **got = unibi_get_aliases(ut);
    if (got && got[0] && strcmp(got[0], "screen") == 0 &&
        got[1] && strcmp(got[1], "test") == 0 && got[2] == NULL) {
        printf("ok 6 - unibi_set_aliases/get_aliases\n");
    } else {
        printf("not ok 6 - unibi_set_aliases/get_aliases\n");
        fails++;
    }

    /* Serialization roundtrip: dump the in-memory terminal then parse it
     * back with unibi_from_mem; all capabilities must survive. */
    size_t n = unibi_dump(ut, buf, sizeof buf);
    if (n == 0) {
        printf("not ok 7 - unibi_dump()\n");
        fails++;
    } else {
        printf("ok 7 - unibi_dump() (%zu bytes)\n", n);
        unibi_term *ut2 = unibi_from_mem(buf, n);
        if (!ut2) {
            printf("not ok 8 - unibi_from_mem()\n");
            fails++;
        } else {
            printf("ok 8 - unibi_from_mem()\n");
            if (unibi_get_bool(ut2, unibi_auto_left_margin) == 1 &&
                unibi_get_num(ut2, unibi_columns) == 80 &&
                unibi_get_str(ut2, unibi_clear_screen) &&
                strcmp(unibi_get_str(ut2, unibi_clear_screen), "\033[H\033[J") == 0) {
                printf("ok 9 - capabilities survive dump/from_mem roundtrip\n");
            } else {
                printf("not ok 9 - capabilities survive dump/from_mem roundtrip\n");
                fails++;
            }
            unibi_destroy(ut2);
        }
    }

    /* Short-name lookup helper. */
    const char *shortname = unibi_short_name_bool(unibi_auto_right_margin);
    if (shortname && strcmp(shortname, "am") == 0) {
        printf("ok 10 - unibi_short_name_bool()\n");
    } else {
        printf("not ok 10 - unibi_short_name_bool()\n");
        fails++;
    }

    /* unibi_run evaluates a terminfo format string on the dumped entry.
     * "%p1%d" with arg 3 must produce "3". */
    unibi_var_t p0 = unibi_var_from_num(3);
    unibi_var_t params[9] = { p0 };
    char out[64];
    size_t r = unibi_run("%p1%d", params, out, sizeof out);
    if (r == 1 && out[0] == '3') {
        printf("ok 11 - unibi_run() format\n");
    } else {
        printf("not ok 11 - unibi_run() format\n");
        fails++;
    }

    unibi_destroy(ut);
    printf("ok 12 - unibi_destroy()\n");

    if (fails) {
        printf("# %d assertion(s) failed\n", fails);
        return 1;
    }
    printf("1..12\n");
    return 0;
}