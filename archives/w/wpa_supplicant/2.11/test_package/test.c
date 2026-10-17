// test_package/test.c - Test for wpa_supplicant 2.11 package
// Verifies the wpa_supplicant binary is functional by executing it
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    // Execute wpa_supplicant --version to verify the binary is functional
    int ret = system("wpa_supplicant --version");
    if (ret != 0) {
        fprintf(stderr, "wpa_supplicant --version failed with code %d\n", ret);
        return 1;
    }
    printf("wpa_supplicant binary test: PASS\n");
    return 0;
}
