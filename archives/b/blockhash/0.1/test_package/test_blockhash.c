/* test_package/test_blockhash.c
 * Verify blockhash binary is available and functional.
 * Compiled by test_package/conanfile.py, calls blockhash --version.
 */
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int ret = system("blockhash --version");
    if (ret != 0) {
        fprintf(stderr, "blockhash --version failed\n");
        return 1;
    }
    printf("blockhash binary is functional\n");
    return 0;
}
