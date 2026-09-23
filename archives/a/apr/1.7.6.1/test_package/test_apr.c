#include <apr_general.h>
#include <apr_pools.h>

int main(void)
{
    apr_pool_t *pool = 0;
    if (apr_initialize() != APR_SUCCESS) return 1;
    if (apr_pool_create(&pool, 0) != APR_SUCCESS) return 2;
    apr_pool_destroy(pool);
    apr_terminate();
    return 0;
}
