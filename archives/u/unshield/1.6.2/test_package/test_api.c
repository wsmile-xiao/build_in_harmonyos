/**
 * test_package/test_api.c — libunshield API smoke test (R34).
 *
 * Compiles a small program that calls a real libunshield function
 * (unshield_open) to verify the library is linkable and usable.
 */
#include <stdio.h>
#include <libunshield.h>

int main(void) {
    Unshield* unshield = unshield_open("nonexistent.cab");
    /* Expected: file doesn't exist, so return NULL */
    if (unshield == NULL) {
        printf("PASS: unshield_open returned NULL for non-existent file\n");
        return 0;
    } else {
        unshield_close(unshield);
        printf("FAIL: unshield_open returned non-NULL (expected NULL)\n");
        return 1;
    }
}