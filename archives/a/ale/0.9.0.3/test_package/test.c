#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* Run ale-bin --version to verify the binary works */
    int ret = system("ale-bin --version");
    if (ret != 0) {
        printf("FAIL: ale-bin --version returned %d\n", ret);
        return 1;
    }
    printf("test ale 0.9.0.3: OK\n");
    return 0;
}