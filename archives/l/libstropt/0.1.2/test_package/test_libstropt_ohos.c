#include <stropt.h>

#include <stdint.h>
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

#define CHECK(condition, name)                         \
    do {                                               \
        ++check_number;                                \
        if (!(condition)) {                            \
            printf("not ok %d - %s\n", check_number, name); \
            return EXIT_FAILURE;                       \
        }                                              \
        printf("ok %d - %s\n", check_number, name); \
    } while (0)

int main(void)
{
    const uint16_t endian_probe = 1;
    char buffer[128];
    char rebuilt[64];
    char *tags[8];
    char *args[8];

    CHECK(sizeof(void *) == 8, "OHOS PC uses a 64-bit ABI");
    CHECK(*(const unsigned char *)&endian_probe == 1, "OHOS aarch64 is little-endian");

    const int count = stropt("alpha=1\nbeta='two three'#tail", tags, args, buffer);
    CHECK(count == 3 && strcmp(tags[0], "alpha") == 0 && strcmp(args[0], "1") == 0 &&
              strcmp(tags[1], "beta") == 0 && strcmp(args[1], "two three") == 0,
          "OHOS musl parses newline, quote, and comment features");

    char *out_tags[] = {"alpha", "beta", NULL};
    char *out_args[] = {"1", "two three", NULL};
    CHECK(stropt2buf(rebuilt, sizeof(rebuilt), out_tags, out_args, ',', '=') == rebuilt &&
              strcmp(rebuilt, "alpha=1,beta=two three") == 0,
          "fixed-buffer reconstruction works on OHOS musl");

    char *allocated = stropt2str(out_tags, out_args, ';', '=');
    CHECK(allocated != NULL && strcmp(allocated, "alpha=1;beta=two three") == 0,
          "dynamic reconstruction works on OHOS musl");
    free(allocated);

    printf("libstropt HarmonyOS test: 5/5 assertions passed\n");
    return EXIT_SUCCESS;
}
