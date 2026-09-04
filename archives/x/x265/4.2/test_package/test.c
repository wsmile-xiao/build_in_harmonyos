#include "x265.h"
#include <stdio.h>

int main(void) {
    x265_param *param = x265_param_alloc();
    if (!param) {
        fprintf(stderr, "Failed to allocate x265_param\n");
        return 1;
    }
    x265_param_default(param);
    printf("x265 param alloc and default: OK\n");
    x265_param_free(param);
    return 0;
}
