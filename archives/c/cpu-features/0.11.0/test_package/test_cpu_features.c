#include <stdio.h>
#include "cpuinfo_aarch64.h"

int main(void) {
    /* 鸿蒙特有验证：在 HarmonyOS PC (aarch64) 上经 getauxval/hwcap 实读
       CPU 特性。ARMv8 强制要求 fp/asimd，若探测链路断裂二者必为 0。 */
    Aarch64Info info = GetAarch64Info();
    printf("implementer=0x%x part=0x%x fp=%d asimd=%d\n",
           info.implementer, info.part,
           info.features.fp, info.features.asimd);
    if (!info.features.fp || !info.features.asimd) {
        printf("FAIL: mandatory ARMv8 features not detected\n");
        return 1;
    }
    printf("PASS: aarch64 cpu features detected on HarmonyOS\n");
    return 0;
}
