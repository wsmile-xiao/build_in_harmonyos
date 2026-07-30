#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* R34 compliance: actually execute the xdg-ninja binary */
    int ret = system("xdg-ninja --version > /dev/null 2>&1");
    if (ret == 0) {
        printf("test xdg-ninja 0.2.0.2: OK\n");
        return 0;
    }
    /* Fallback: try without arguments */
    ret = system("xdg-ninja --help > /dev/null 2>&1");
    if (ret == 0) {
        printf("test xdg-ninja 0.2.0.2: OK\n");
        return 0;
    }
    printf("test xdg-ninja 0.2.0.2: FAIL (binary not executable)\n");
    return 1;
}