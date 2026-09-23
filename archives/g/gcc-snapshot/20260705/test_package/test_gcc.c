#include <stdint.h>
#include <stdio.h>
#include <string.h>

#if defined(EXPECT_OHOS) && !defined(__OHOS__)
#error "The HarmonyOS GCC target must define __OHOS__"
#endif

int main(void)
{
    volatile uint64_t value = UINT64_C(0x123456789abcdef0);
    const volatile unsigned char *bytes =
        (const volatile unsigned char *)&value;
    char message[32];

    if (sizeof(void *) != 8) {
        return 1;
    }
    if (bytes[0] != 0xf0 || bytes[7] != 0x12) {
        return 2;
    }
    if (snprintf(message, sizeof(message), "gcc%u-ohos-ok", 17U) != 13 ||
        strcmp(message, "gcc17-ohos-ok") != 0) {
        return 3;
    }
    puts(message);
    return 0;
}
