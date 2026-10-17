#include <stdio.h>
#include <stdlib.h>
#include "signal_protocol.h"
#include "curve.h"

int main(void) {
    signal_context *ctx = NULL;
    int ret = signal_context_create(&ctx, NULL);
    if (ret != 0) {
        fprintf(stderr, "signal_context_create failed: %d\n", ret);
        return 1;
    }

    int t = curve_internal_fast_tests(1);
    if (t != 0) {
        fprintf(stderr, "curve_internal_fast_tests failed: %d\n", t);
        signal_context_destroy(ctx);
        return 1;
    }

    // Also test basic key generation with a simple random provider
    // Use a stub random that returns deterministic bytes for smoke test
    // If curve generation needs crypto provider, we test provider wiring minimally
    // For now, internal tests are enough to prove linkage and core crypto

    signal_context_destroy(ctx);
    printf("libomemo-c smoke test passed: curve_internal_fast_tests=0\n");
    return 0;
}
