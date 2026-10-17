#include <shhopt.h>

#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef __OHOS__
#error "This test must be compiled by the HarmonyOS toolchain"
#endif

#ifndef __aarch64__
#error "This test targets HarmonyOS PC aarch64"
#endif

static int check_number;

#define CHECK(condition, name)                              \
    do {                                                    \
        ++check_number;                                     \
        if (!(condition)) {                                 \
            printf("not ok %d - %s\n", check_number, name); \
            return EXIT_FAILURE;                            \
        }                                                   \
        printf("ok %d - %s\n", check_number, name);        \
    } while (0)

int main(void)
{
    long minimum = 0;
    long maximum = 0;
    unsigned long unsigned_maximum = 0;
    optStruct options[] = {
        {'m', "minimum", OPT_LONG, &minimum, 0},
        {'M', "maximum", OPT_LONG, &maximum, 0},
        {'U', "unsigned-maximum", OPT_ULONG, &unsigned_maximum, 0},
        {0, NULL, OPT_END, NULL, 0}
    };
    int argc = 6;
    char min_text[32];
    char max_text[32];
    char umax_text[32];
    char *argv[] = {
        "consumer", "--minimum", min_text, "--maximum", max_text,
        "--unsigned-maximum", umax_text, NULL
    };

    snprintf(min_text, sizeof(min_text), "%ld", LONG_MIN);
    snprintf(max_text, sizeof(max_text), "%ld", LONG_MAX);
    snprintf(umax_text, sizeof(umax_text), "%lu", ULONG_MAX);
    argc = 7;

    CHECK(sizeof(long) == 8 && sizeof(void *) == 8,
          "HarmonyOS PC uses the LP64 data model");
    optParseOptions(&argc, argv, options, 0);
    CHECK(minimum == LONG_MIN, "parse HarmonyOS LP64 LONG_MIN");
    CHECK(maximum == LONG_MAX, "parse HarmonyOS LP64 LONG_MAX");
    CHECK(unsigned_maximum == ULONG_MAX, "parse HarmonyOS LP64 ULONG_MAX");

    {
        int negative_argc = 3;
        char *negative_argv[] = {"consumer", "-9223372036854775807", "tail", NULL};
        optParseOptions(&negative_argc, negative_argv, options, 1);
        CHECK(negative_argc == 3 &&
                  strcmp(negative_argv[1], "-9223372036854775807") == 0,
              "allowNegNum preserves a HarmonyOS 64-bit negative argument");
    }

    printf("shhopt HarmonyOS test: 5/5 assertions passed\n");
    return EXIT_SUCCESS;
}
