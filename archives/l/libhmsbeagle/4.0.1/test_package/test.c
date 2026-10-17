#include <stdio.h>
#include <string.h>
#include <libhmsbeagle/beagle.h>

int main(void) {
    int failed = 0;

    /* 1: version string must exist and match 4.0.1 */
    const char *ver = beagleGetVersion();
    if (ver == NULL || ver[0] == '\0') {
        printf("FAIL: beagleGetVersion returned NULL/empty\n");
        failed = 1;
    } else {
        printf("beagle version: %s\n", ver);
        if (strstr(ver, "4.0.1") == NULL) {
            printf("FAIL: version does not contain 4.0.1\n");
            failed = 1;
        } else {
            printf("CHECK-OK: beagleGetVersion\n");
        }
    }

    /* 2: citation string must exist */
    const char *cite = beagleGetCitation();
    if (cite == NULL || cite[0] == '\0') {
        printf("FAIL: beagleGetCitation returned NULL/empty\n");
        failed = 1;
    } else {
        printf("beagle citation OK (%.40s...)\n", cite);
        printf("CHECK-OK: beagleGetCitation\n");
    }

    /* 3: resource list must exist with at least CPU resource */
    BeagleResourceList *rl = beagleGetResourceList();
    if (rl == NULL) {
        printf("FAIL: beagleGetResourceList returned NULL\n");
        failed = 1;
    } else if (rl->length < 1 || rl->list == NULL || rl->list[0].name == NULL) {
        printf("FAIL: resource list empty (length=%d)\n", rl ? rl->length : -1);
        failed = 1;
    } else {
        printf("resources: length=%d first=%s\n", rl->length, rl->list[0].name);
        printf("CHECK-OK: beagleGetResourceList\n");
    }

    if (failed == 0) {
        printf("libhmsbeagle smoke: all 3 checks passed\n");
    }
    return failed;
}
