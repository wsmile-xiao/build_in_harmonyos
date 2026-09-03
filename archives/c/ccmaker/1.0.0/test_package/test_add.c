#include "ccmaker.h"
#include <stdio.h>

int main(void) {
    int r1 = ccmaker_add(2, 3);
    int r2 = ccmaker_add(-1, 1);
    int r3 = ccmaker_sub(5, 3);
    if (r1 != 5) {
        fprintf(stderr, "add 2+3 expected 5 got %d\n", r1);
        return 1;
    }
    if (r2 != 0) {
        fprintf(stderr, "add -1+1 expected 0 got %d\n", r2);
        return 1;
    }
    if (r3 != 2) {
        fprintf(stderr, "sub 5-3 expected 2 got %d\n", r3);
        return 1;
    }
    printf("test_add passed: 2+3=5, sub 5-3=2\n");
    return 0;
}
