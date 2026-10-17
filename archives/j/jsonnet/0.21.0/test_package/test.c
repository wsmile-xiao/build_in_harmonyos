#include <stdio.h>
#include <string.h>
#include "libjsonnet.h"

int main(void) {
    struct JsonnetVm *vm = jsonnet_make();
    if (vm == NULL) {
        fprintf(stderr, "Failed to create Jsonnet VM\n");
        return 1;
    }

    /* Verify version string */
    const char *ver = jsonnet_version();
    printf("Jsonnet version: %s\n", ver);

    /* Evaluate a simple expression */
    int error;
    char *result = jsonnet_evaluate_snippet(
        vm, "test", "{ \"hello\": \"world\" }", &error
    );

    if (error != 0) {
        fprintf(stderr, "Jsonnet evaluation failed: %s\n", result);
        jsonnet_realloc(vm, result, 0);
        jsonnet_destroy(vm);
        return 1;
    }

    printf("Result: %s\n", result);

    /* Verify expected output */
    if (strstr(result, "hello") == NULL || strstr(result, "world") == NULL) {
        fprintf(stderr, "Unexpected result: %s\n", result);
        jsonnet_realloc(vm, result, 0);
        jsonnet_destroy(vm);
        return 1;
    }

    jsonnet_realloc(vm, result, 0);
    jsonnet_destroy(vm);

    printf("jsonnet test: PASS\n");
    return 0;
}
