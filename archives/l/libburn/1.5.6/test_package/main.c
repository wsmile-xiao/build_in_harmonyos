#include <libburn/libburn.h>
#include <stdio.h>

int main(void) {
    int major = 0, minor = 0, micro = 0;

    /* Assertion 1: burn_version fills in version numbers */
    burn_version(&major, &minor, &micro);

    /* Assertion 2: version numbers match 1.5.6 */
    if (major != 1 || minor != 5 || micro != 6) {
        fprintf(stderr, "FAIL: version %d.%d.%d != 1.5.6\n", major, minor, micro);
        return 1;
    }

    printf("libburn version: %d.%d.%d\n", major, minor, micro);

    /* Assertion 3: burn_abort completes without crash (patience=-1, no pacifier) */
    int ret = burn_abort(-1, NULL, NULL);
    if (ret < 0) {
        fprintf(stderr, "FAIL: burn_abort returned %d\n", ret);
        return 2;
    }

    printf("All libburn smoke tests passed.\n");
    return 0;
}
