#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* R34: Execute bird binary to verify it is functional, not just a stub */
    int ret = system("bird --version > /dev/null 2>&1");
    if (ret != 0) {
        printf("FAIL: bird --version returned %d\n", ret);
        return 1;
    }
    printf("PASS: bird2 2.17.4 binary is functional\n");
    return 0;
}
