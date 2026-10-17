#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int ret = system("c3c --version");
    if (ret != 0) {
        printf("FAIL: c3c --version returned %d\n", ret);
        return 1;
    }
    printf("test c3c 0.8.1: OK\n");
    return 0;
}