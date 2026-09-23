#include <stdio.h>
#include <string.h>

#include "cpu_features/cpu_features_macros.h"
#include "cpu_features/cpuinfo_aarch64.h"
#include "cpu_features/cpu_features_cache_info.h"

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

    if (failures == 0) {
        printf("test cpu_features 0.9.0: OK "
               "(implementer=%d part=%d features.fp=%d features.asimd=%d)\n",
               info.implementer, info.part, info.features.fp,
               info.features.asimd);
        return 0;
    }
    printf("test cpu_features 0.9.0: FAILED (%d checks)\n", failures);
    return 1;
}
