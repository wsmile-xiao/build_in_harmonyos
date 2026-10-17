/* R34 consumer: links against the packaged libjte and exercises its public
 * API, so the test fails loudly if the library is missing or mis-exported. */
#include <stdio.h>
#include <string.h>

#include "libjte.h"

int main(void)
{
    struct libjte_env *env = NULL;
    int major = -1, minor = -1, micro = -1;
    int rc;

    libjte__version(&major, &minor, &micro);
    printf("LIBJTE-VERSION %d.%d.%d\n", major, minor, micro);
    if (major < 2) {
        fprintf(stderr, "unexpected libjte major version %d\n", major);
        return 1;
    }
    if (!libjte__is_compatible(major, minor, micro, 0)) {
        fprintf(stderr, "libjte__is_compatible rejected its own version\n");
        return 2;
    }
    /* libjte returns >0 on success throughout its API. */
    rc = libjte_new(&env, 0);
    if (rc <= 0 || env == NULL) {
        fprintf(stderr, "libjte_new failed rc=%d\n", rc);
        return 3;
    }
    rc = libjte_set_verbose(env, 0);
    if (rc <= 0) {
        fprintf(stderr, "libjte_set_verbose failed rc=%d\n", rc);
        (void)libjte_destroy(&env);
        return 4;
    }
    rc = libjte_destroy(&env);
    if (rc <= 0) {
        fprintf(stderr, "libjte_destroy failed rc=%d\n", rc);
        return 5;
    }
    if (env != NULL) {
        fprintf(stderr, "libjte_destroy did not clear the handle\n");
        return 6;
    }
    printf("CONSUMER-OK\n");
    return 0;
}
