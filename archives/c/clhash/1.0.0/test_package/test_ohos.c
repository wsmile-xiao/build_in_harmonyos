#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/utsname.h>

#include "clhash.h"

static int check(int condition, const char *message) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    printf("PASS: %s\n", message);
    return 0;
}

int main(void) {
#if !defined(__OHOS__)
    fprintf(stderr, "FAIL: test_ohos must be compiled for OpenHarmony\n");
    return 1;
#endif

    int failures = 0;
    struct utsname system_info;
    failures += check(uname(&system_info) == 0,
                      "OpenHarmony runtime exposes uname");
    if (failures == 0) {
        failures += check(strcmp(system_info.sysname, "HarmonyOS") == 0,
                          "runtime identifies HarmonyOS");
    }

    void *key = get_random_key_for_clhash(UINT64_C(11), UINT64_C(29));
    const unsigned char input[] = "OpenHarmony clhash";
    failures += check(key != NULL, "clhash key allocation works on HarmonyOS");
    if (key != NULL) {
        failures += check(clhash(key, (const char *)input, sizeof(input) - 1) != 0,
                          "clhash executes on the HarmonyOS consumer path");
        free(key);
    }

    if (failures != 0) {
        fprintf(stderr, "HarmonyOS-specific clhash test failed: %d checks\n", failures);
        return 1;
    }
    printf("HarmonyOS-specific clhash test: all 4 checks passed\n");
    return 0;
}
