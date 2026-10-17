#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <libfixmath/fix16.h>

#ifndef __OHOS__
#error "This test must be compiled for HarmonyOS/OpenHarmony"
#endif

#ifndef __aarch64__
#error "HarmonyOS PC package must target AArch64"
#endif

/* musl does not guarantee a predefined identifier in every toolchain. */
#ifdef __GLIBC__
#error "HarmonyOS native SDK must not expose the glibc ABI"
#endif

#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "HarmonyOS PC target must use little-endian byte order"
#endif

_Static_assert(sizeof(fix16_t) == 4, "fix16_t ABI must remain 32-bit");
_Static_assert(sizeof(void *) == 8, "HarmonyOS PC AArch64 pointers must be 64-bit");

static int expect_equal(const char *name, fix16_t actual, fix16_t expected)
{
    if (actual == expected) {
        return 0;
    }

    fprintf(stderr, "%s: got %d, expected %d\n", name, actual, expected);
    return 1;
}

int main(void)
{
    int failures = 0;
    char buffer[24] = {0};

    failures += expect_equal("negative multiplication",
                             fix16_mul(F16(-7.5), F16(0.5)), F16(-3.75));
    failures += expect_equal("fractional division",
                             fix16_div(F16(7.0), F16(8.0)), F16(0.875));
    failures += expect_equal("leading-space parsing",
                             fix16_from_str(" \t-12.5"), F16(-12.5));

    fix16_to_str(F16(123.125), buffer, 3);
    if (strcmp(buffer, "123.125") != 0) {
        fprintf(stderr, "string conversion: got %s, expected 123.125\n", buffer);
        ++failures;
    }

    if (failures != 0) {
        return 1;
    }

    puts("libfixmath HarmonyOS AArch64 ABI: PASS");
    return 0;
}
