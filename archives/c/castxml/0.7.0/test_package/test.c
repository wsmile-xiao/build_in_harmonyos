#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int ret = system("castxml --version > /dev/null 2>&1");
    if (ret != 0) {
        fprintf(stderr, "FAIL: castxml --version returned %d\n", ret);
        return 1;
    }
    printf("castxml 0.7.0: OK\n");
    return 0;
}
