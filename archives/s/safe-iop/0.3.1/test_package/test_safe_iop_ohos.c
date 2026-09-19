#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/types.h>

#include <safe_iop.h>

#ifndef __OHOS__
#error "This test must be compiled by the HarmonyOS toolchain"
#endif

#ifndef __aarch64__
#error "The HarmonyOS PC package requires the AArch64 target"
#endif

#define CHECK(condition)                                                      \
    do {                                                                      \
        if (!(condition)) {                                                   \
            fprintf(stderr, "OHOS CHECK failed: %s (line %d)\n",            \
                    #condition, __LINE__);                                    \
            return 1;                                                         \
        }                                                                     \
    } while (0)

int main(void) {
    size_t size_result = 0;
    unsigned long ulong_result = 0;
    long signed_long_result = 0;
    uint32_t formatted_result = 0;

    CHECK(sizeof(size_t) == 8 && sizeof(ssize_t) == 8 && sizeof(long) == 8);
    CHECK(safe_add(&size_result, (size_t)SIZE_MAX, (size_t)1) == 0);
    CHECK(safe_mul(&ulong_result, (unsigned long)ULONG_MAX,
                   (unsigned long)2) == 0);
    CHECK(safe_add(&signed_long_result, (long)LONG_MAX, (long)1) == 0);
    CHECK(safe_iopf(&formatted_result, "u32*", (uint32_t)4096,
                    (uint32_t)4096) == 1 && formatted_result == 16777216U);

    puts("safe-iop HarmonyOS armv8 checks: 5/5 passed");
    return 0;
}
