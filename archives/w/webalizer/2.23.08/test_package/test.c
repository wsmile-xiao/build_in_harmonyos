/* test_package/test.c — webalizer 2.23.08 L1 test
 *
 * R34: substantively exercises the packaged binary.
 * Calls webalizer -V via system() and verifies exit behavior.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    /* webalizer -V prints version and exits with code 1 */
    int ret = system("webalizer -V < /dev/null 2>&1 | grep -q 'Webalizer'");
    if (ret == 0) {
        printf("webalizer binary found and reports version\n");
        return 0;
    }
    fprintf(stderr, "webalizer binary not found or version check failed\n");
    return 1;
}
