#include <stdio.h>
#include <string.h>
#include "tng/tng_io.h"

/* Consumer test for libtng_io 1.8.2 (R34: must call real public API).
 * Verifies that the installed headers/library can be consumed and that
 * the library performs real work: trajectory init, version query and
 * destroy round-trip through the public API. */
int main(void)
{
    tng_trajectory_t traj = NULL;
    char version_str[TNG_MAX_STR_LEN];
    tng_function_status st;

    st = tng_trajectory_init(&traj);
    if (st != TNG_SUCCESS || traj == NULL)
    {
        printf("FAIL: tng_trajectory_init returned %d\n", (int) st);
        return 1;
    }

    st = tng_version(traj, version_str, TNG_MAX_STR_LEN);
    if (st != TNG_SUCCESS)
    {
        printf("FAIL: tng_version returned %d\n", (int) st);
        return 1;
    }
    printf("TNG version: %s\n", version_str);
    if (strstr(version_str, "1.8") == NULL)
    {
        printf("FAIL: unexpected version string\n");
        return 1;
    }

    st = tng_trajectory_destroy(&traj);
    if (st != TNG_SUCCESS || traj != NULL)
    {
        printf("FAIL: tng_trajectory_destroy returned %d\n", (int) st);
        return 1;
    }

    printf("test tng 1.8.2: OK\n");
    return 0;
}
