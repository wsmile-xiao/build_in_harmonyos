#include <stdio.h>
#include <string.h>

#include "cpu_features/cpu_features_macros.h"
#include "cpu_features/cpuinfo_aarch64.h"

int main(void) {
    /* Real consumer usage of the cpu_features C API on aarch64. */
    const Aarch64Info info = GetAarch64Info();

    int failures = 0;

    /* implementer/variant/part/revision are populated from /proc/cpuinfo on
       Linux/OHOS; they must be non-negative. */
    if (info.implementer < 0) {
        fprintf(stderr, "FAIL: implementer < 0 (%d)\n", info.implementer);
        failures++;
    }
    /* A real CPU always has at least the base FP/ASIMD features, and
       features.fp reflects CPU_FEATURES_AARCH64_FP. */
    if (info.features.fp == 0) {
        fprintf(stderr, "FAIL: fp feature not detected\n");
        failures++;
    }
    if (info.features.asimd == 0) {
        fprintf(stderr, "FAIL: asimd feature not detected\n");
        failures++;
    }

    /* The string utility layer is part of the public API surface. */
    const char* last = GetAarch64FeaturesEnumName(AARCH64_LAST_);
    if (last == NULL || strcmp(last, "unknown_feature") != 0) {
        fprintf(stderr, "FAIL: AARCH64_LAST_ enum name mismatch\n");
        failures++;
    }

    /* 0.11.0 delta: new feature bits appended to Aarch64Features (mops,
       hbc, lse128, ...).  GetAarch64FeaturesEnumValue returns the raw
       bitfield value (a signed int : 1 field), not a normalized boolean.
       On some compilers a set int:1 bitfield reads back as -1 (sign
       extension), so the valid return is any non-zero value (feature
       present) or zero (absent) — not strictly 0 or 1.  This is the
       same semantics used by the fp/asimd checks above. */
    const int poe = GetAarch64FeaturesEnumValue(&info.features, AARCH64_POE);
    if (poe != 0 && poe != 1 && poe != -1) {
        fprintf(stderr, "FAIL: AARCH64_POE enum value out of range (%d)\n",
                poe);
        failures++;
    }
    const char* poe_name = GetAarch64FeaturesEnumName(AARCH64_POE);
    if (poe_name == NULL || strcmp(poe_name, "unknown_feature") == 0) {
        fprintf(stderr, "FAIL: AARCH64_POE enum name missing\n");
        failures++;
    }

    if (failures == 0) {
        printf("test cpu_features 0.11.0: OK "
               "(implementer=%d part=%d features.fp=%d features.asimd=%d "
               "poe=%d)\n",
               info.implementer, info.part, info.features.fp,
               info.features.asimd, poe);
        return 0;
    }
    printf("test cpu_features 0.11.0: FAILED (%d checks)\n", failures);
    return 1;
}
