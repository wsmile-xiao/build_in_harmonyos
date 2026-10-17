/* Simple consumer test for libselinux.
 * Verifies that the library can be linked and that basic
 * context manipulation functions (no kernel dependency) are callable. */
#include <selinux/context.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int failures = 0;

    /* Test 1: context_new/context_str (pure library, no kernel) */
    context_t ctx = context_new("u:object_r:test_t:s0");
    if (!ctx) {
        fprintf(stderr, "FAIL: context_new returned NULL\n");
        failures++;
    } else {
        const char *str = context_str(ctx);
        if (!str) {
            fprintf(stderr, "FAIL: context_str returned NULL\n");
            failures++;
        } else {
            printf("OK: context_str = %s\n", str);
        }
        context_free(ctx);
    }

    if (failures == 0) {
        printf("ALL TESTS PASSED\n");
        return 0;
    }
    fprintf(stderr, "%d TEST(S) FAILED\n", failures);
    return 1;
}