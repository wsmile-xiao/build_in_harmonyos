#include <ctapi.h>

#include <stdint.h>

#ifndef __OHOS__
#error "This test must be compiled by the HarmonyOS toolchain"
#endif

#ifndef __aarch64__
#error "The HarmonyOS PC package must target aarch64"
#endif

_Static_assert(sizeof(uint8_t) == 1U, "CT-API byte type must be 8 bits");
_Static_assert(sizeof(uint16_t) == 2U, "CT-API length type must be 16 bits");
_Static_assert(sizeof(int8_t) == 1U, "CT-API status type must be 8 bits");
_Static_assert(ERR_HTSI == -128, "CT-API status must fit int8_t on OHOS");
_Static_assert(ICC14 == 0x0e, "CT-API terminal address changed on OHOS");

int main(void)
{
    int8_t status = ERR_MEMORY;
    uint16_t response_length = 65535U;

    if (status != -11) {
        return 1;
    }
    if (response_length != UINT16_MAX) {
        return 2;
    }
    return (OK == 0 && CT == 0x01 && HOST == 0x02) ? 0 : 3;
}
