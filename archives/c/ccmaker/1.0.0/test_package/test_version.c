#include "ccmaker.h"
#include <stdio.h>
#include <string.h>

int main(void) {
    const char *v = ccmaker_version();
    if (!v) {
        fprintf(stderr, "version is null\n");
        return 1;
    }
    if (strcmp(v, "1.0.0") != 0) {
        fprintf(stderr, "version expected 1.0.0 got %s\n", v);
        return 1;
    }
    printf("test_version passed: %s\n", v);
    return 0;
}
