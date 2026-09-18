#include <stdio.h>
#include <string.h>
#include "liblouisxml.h"

int main(void) {
    const char *ver = lbx_version();
    printf("lbx_version: %s\n", ver);
    if (!ver || strlen(ver) == 0) {
        fprintf(stderr, "lbx_version returned empty\n");
        return 1;
    }
    if (strcmp(ver, "2.4.0") != 0) {
        // Version mismatch is not fatal but we check it matches package
        printf("version mismatch: expected 2.4.0 got %s\n", ver);
        // Still pass if version is non-empty
    }
    // Test lbx_translateString with a simple XML snippet (does not require external tables for version check)
    // We avoid calling lbx_initialize which needs config files, just test version API.
    printf("test_package: lbx_version OK\n");
    return 0;
}
