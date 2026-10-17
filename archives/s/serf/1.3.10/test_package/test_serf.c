#include <stdio.h>

#include <apr.h>
#include <apr_pools.h>

#include "serf.h"

#define CHECK(n, cond) do { \
    if (cond) { printf("ok %d\n", (n)); } \
    else { printf("not ok %d\n", (n)); failed = 1; } \
} while (0)

int main(void)
{
    apr_pool_t *pool = NULL;
    serf_context_t *ctx = NULL;
    serf_bucket_alloc_t *alloc = NULL;
    const char *msg;
    int major = 0, minor = 0, patch = 0;
    int failed = 0;

    CHECK(1, apr_initialize() == APR_SUCCESS);
    CHECK(2, apr_pool_create(&pool, NULL) == APR_SUCCESS && pool != NULL);

    ctx = serf_context_create(pool);
    CHECK(3, ctx != NULL);

    alloc = serf_bucket_allocator_create(pool, NULL, NULL);
    CHECK(4, alloc != NULL);

    msg = serf_error_string(SERF_ERROR_CLOSING);
    CHECK(5, msg != NULL);

    CHECK(6, SERF_MAJOR_VERSION == 1 && SERF_MINOR_VERSION == 3
             && SERF_PATCH_VERSION == 10);

    serf_lib_version(&major, &minor, &patch);
    CHECK(7, major == 1 && minor == 3 && patch == 10);

    CHECK(8, SERF_VERSION_AT_LEAST(1, 3, 10));

    apr_pool_destroy(pool);
    apr_terminate();

    if (!failed) {
        printf("serf consumer smoke: all 8 checks passed\n");
    }
    return failed;
}
