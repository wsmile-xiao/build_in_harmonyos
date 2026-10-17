#include <stdio.h>

#if !defined(__OHOS__)
#error "test_cpipe_ohos must be compiled by the HarmonyOS toolchain"
#endif

#if !defined(__aarch64__)
#error "cpipe HarmonyOS package must target AArch64"
#endif

_Static_assert(sizeof(void *) == 8, "HarmonyOS AArch64 requires a 64-bit ABI");
_Static_assert(__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__,
               "HarmonyOS AArch64 must be little-endian");

int main(void) {
    puts("HARMONYOS_CPIPE_TEST_OK arch=aarch64 abi=64 endian=little");
    return 0;
}
