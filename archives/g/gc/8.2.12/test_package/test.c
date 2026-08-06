/*
 * test_package/test.c — Conan L1 test for gc (Boehm GC) 8.2.12
 *
 * This test exercises the core GC API:
 *   - GC_Init()        : initialize the collector
 *   - GC_malloc()      : allocate garbage-collected memory
 *   - GC_register_finalizer() : register a finalizer callback
 *   - GC_gcollect()    : force a collection cycle
 *
 * R34: test must substantively depend on the tested package's API.
 */

#include <stdio.h>
#include <string.h>
#include <gc.h>

/* Finalizer callback — called when object is collected. */
static int finalizer_called = 0;

static void my_finalizer(void *obj, void *client_data) {
    (void)obj;
    (void)client_data;
    finalizer_called = 1;
}

int main(void) {
    /* Initialize the garbage collector. */
    GC_INIT();

    /* Allocate memory using GC_malloc (will be auto-collected). */
    char *buf = (char *)GC_malloc(128);
    if (!buf) {
        fprintf(stderr, "FAIL: GC_malloc returned NULL\n");
        return 1;
    }

    /* Write to the allocated memory to verify it is usable. */
    strcpy(buf, "Hello from Boehm GC!");
    if (strcmp(buf, "Hello from Boehm GC!") != 0) {
        fprintf(stderr, "FAIL: memory content mismatch\n");
        return 1;
    }

    /* Allocate atomic (no-pointer) memory. */
    int *nums = (int *)GC_malloc_atomic(10 * sizeof(int));
    if (!nums) {
        fprintf(stderr, "FAIL: GC_malloc_atomic returned NULL\n");
        return 1;
    }
    for (int i = 0; i < 10; i++) {
        nums[i] = i * 42;
    }
    if (nums[5] != 210) {
        fprintf(stderr, "FAIL: atomic memory content mismatch\n");
        return 1;
    }

    /* Register a finalizer on an object. */
    char *fin_obj = (char *)GC_malloc(64);
    if (!fin_obj) {
        fprintf(stderr, "FAIL: GC_malloc for finalizer test returned NULL\n");
        return 1;
    }
    GC_REGISTER_FINALIZER(fin_obj, my_finalizer, NULL, NULL, NULL);

    /* Drop references — objects become eligible for collection. */
    buf = NULL;
    nums = NULL;
    fin_obj = NULL;

    /* Force a garbage collection cycle. */
    GC_gcollect();
    GC_invoke_finalizers();

    /* Verify finalizer was called. */
    if (!finalizer_called) {
        fprintf(stderr, "FAIL: finalizer was not called\n");
        return 1;
    }

    /* Verify basic functionality succeeded. */
    printf("PASS: GC_Init, GC_malloc, GC_malloc_atomic, GC_gcollect, finalizer all OK\n");
    return 0;
}
