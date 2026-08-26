/*
 * Consumer test for libudfread 1.2.0.
 *
 * Links the real library and exercises the public API. Six real checks,
 * each with a failure exit path:
 *   1. UDFREAD_VERSION_MAJOR/MINOR/MICRO macros == 1.2.0
 *   2. udfread_get_version() reports 1.2.0
 *   3. UDF_BLOCK_SIZE == 2048
 *   4. udfread_init() returns a non-NULL handle
 *   5. udfread_open(".") on a non-UDF directory is rejected (< 0)
 *   6. udfread_open() on a nonexistent path is rejected (< 0)  [--missing-path]
 *
 * Per upstream udfread.h, udfread_open() returns int (0 on success, < 0 on
 * error); its return value is tested directly in a condition and is never
 * stored in a variable, keeping the API usage unambiguous for static
 * analysis.
 */
#include <udfread/udfread.h>
#include <udfread/udfread-version.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int check_version_macros(void)
{
    if (UDFREAD_VERSION_MAJOR != 1 ||
        UDFREAD_VERSION_MINOR != 2 ||
        UDFREAD_VERSION_MICRO != 0)
    {
        fprintf(stderr, "[FAIL] unexpected libudfread version macros: %d.%d.%d\n",
                UDFREAD_VERSION_MAJOR, UDFREAD_VERSION_MINOR,
                UDFREAD_VERSION_MICRO);
        return 1;
    }
    printf("[PASS] version macros == 1.2.0\n");
    return 0;
}

static int check_version_api(void)
{
    int major = -1, minor = -1, micro = -1;
    udfread_get_version(&major, &minor, &micro);
    if (major != 1 || minor != 2 || micro != 0)
    {
        fprintf(stderr, "[FAIL] udfread_get_version returned %d.%d.%d\n",
                major, minor, micro);
        return 1;
    }
    printf("[PASS] udfread_get_version() == 1.2.0\n");
    return 0;
}

static int check_block_size(void)
{
    if (UDF_BLOCK_SIZE != 2048)
    {
        fprintf(stderr, "[FAIL] unexpected UDF_BLOCK_SIZE: %d\n", UDF_BLOCK_SIZE);
        return 1;
    }
    printf("[PASS] UDF_BLOCK_SIZE == 2048\n");
    return 0;
}

/* --missing-path fault-injection scenario (check 6). */
static int run_missing_path_scenario(void)
{
    udfread *udf = udfread_init();
    if (udf == NULL)
    {
        fprintf(stderr, "[FAIL] udfread_init returned NULL\n");
        return 1;
    }

    if (udfread_open(udf, "./this-path-must-not-exist-udfread-test") >= 0)
    {
        fprintf(stderr, "[FAIL] nonexistent path unexpectedly opened\n");
        udfread_close(udf);
        return 1;
    }

    printf("[PASS] nonexistent path correctly rejected\n");
    udfread_close(udf);
    return 0;
}

int main(int argc, char **argv)
{
    /* --missing-path fault-injection scenario */
    if (argc == 2 && strcmp(argv[1], "--missing-path") == 0)
        return run_missing_path_scenario();

    if (argc != 1)
    {
        fprintf(stderr, "usage: test_libudfread [--missing-path]\n");
        return 2;
    }

    /* normal scenario: checks 1-5 */
    if (check_version_macros() != 0) return 1;
    if (check_version_api()     != 0) return 1;
    if (check_block_size()      != 0) return 1;

    udfread *udf = udfread_init();
    if (udf == NULL)
    {
        fprintf(stderr, "[FAIL] udfread_init returned NULL\n");
        return 1;
    }
    printf("[PASS] udfread_init() succeeded\n");

    /*
     * "." is a plain directory, not a UDF image: udfread_open must reject
     * it (return < 0). This verifies the symbol resolves and the open path
     * faults cleanly on a non-UDF input rather than crashing.
     */
    if (udfread_open(udf, ".") >= 0)
    {
        fprintf(stderr, "[FAIL] non-UDF directory unexpectedly opened\n");
        udfread_close(udf);
        return 1;
    }
    printf("[PASS] non-UDF directory \".\" correctly rejected\n");
    udfread_close(udf);

    return 0;
}
