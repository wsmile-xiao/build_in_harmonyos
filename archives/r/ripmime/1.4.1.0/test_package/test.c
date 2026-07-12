#include <stdlib.h>
#include <stdio.h>

int main(void) {
    int ret = system("ripmime --version");
    if (ret != 0) {
        fprintf(stderr, "ripmime --version failed\n");
        return 1;
    }
    printf("ripmime smoke test passed\n");
    return 0;
}
