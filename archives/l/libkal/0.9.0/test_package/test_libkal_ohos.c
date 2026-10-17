#include <stdio.h>

#include "kal.h"

#ifndef __OHOS__
#error "This test must be compiled by the HarmonyOS toolchain"
#endif

#ifndef __aarch64__
#error "HarmonyOS PC libkal validation requires aarch64"
#endif

#if !defined(__LP64__) && !defined(_LP64)
#error "HarmonyOS PC libkal validation requires the LP64 data model"
#endif

int main(void)
{
    int day = 0;
    int month = 0;
    int year = 0;
    long jd;

    if (sizeof(long) != 8 || sizeof(void *) != 8) {
        fprintf(stderr, "unexpected HarmonyOS ABI: long=%zu pointer=%zu\n",
                sizeof(long), sizeof(void *));
        return 1;
    }

    jd = kal_conv_gre_jd(1, 1, 2000);
    kal_conv_jd_gre(jd, &day, &month, &year);
    if (jd != 2451545 || day != 1 || month != 1 || year != 2000) {
        fprintf(stderr, "packaged libkal failed on HarmonyOS\n");
        return 1;
    }

    puts("libkal HarmonyOS aarch64 LP64 test passed");
    return 0;
}
