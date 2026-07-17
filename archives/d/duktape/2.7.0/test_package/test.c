#include <stdio.h>
#include "duktape.h"

int main(void) {
    duk_context *ctx = duk_create_heap_default();
    if (!ctx) {
        fprintf(stderr, "Failed to create duktape heap\n");
        return 1;
    }

    /* Test 1: Evaluate a simple arithmetic expression */
    if (duk_peval_string(ctx, "2 + 3") != 0) {
        fprintf(stderr, "Eval failed: %s\n", duk_safe_to_string(ctx, -1));
        duk_pop(ctx);
        duk_destroy_heap(ctx);
        return 1;
    }
    duk_int_t result = duk_get_int(ctx, -1);
    duk_pop(ctx);

    if (result != 5) {
        fprintf(stderr, "Test failed: expected 5, got %d\n", result);
        duk_destroy_heap(ctx);
        return 1;
    }

    /* Test 2: Check Duktape.version is available */
    if (duk_peval_string(ctx, "Duktape.version") != 0) {
        fprintf(stderr, "Eval failed: %s\n", duk_safe_to_string(ctx, -1));
        duk_pop(ctx);
        duk_destroy_heap(ctx);
        return 1;
    }
    duk_int_t version = duk_get_int(ctx, -1);
    duk_pop(ctx);

    if (version != 20700) {
        fprintf(stderr, "Test failed: expected version 20700, got %d\n", version);
        duk_destroy_heap(ctx);
        return 1;
    }

    printf("duktape test passed: 2+3=%d, version=%d\n", result, version);
    duk_destroy_heap(ctx);
    return 0;
}
