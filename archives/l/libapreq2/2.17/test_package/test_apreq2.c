#include <stdio.h>
#include <string.h>

#include <apr_general.h>
#include <apr_pools.h>
#include <apr_tables.h>

#include <apreq.h>
#include <apreq_cookie.h>
#include <apreq_version.h>

int main(void)
{
    apr_pool_t *pool = NULL;
    const char *vstring;
    apr_table_t *jar;
    const char *val;
    int total = 2;
    int passed = 0;

    if (apr_initialize() != APR_SUCCESS) {
        printf("[1/2] apr_initialize: FAIL\n");
        printf("RESULT: 0/%d passed\n", total);
        return 1;
    }
    if (apr_pool_create(&pool, NULL) != APR_SUCCESS) {
        printf("[1/2] apr_pool_create: FAIL\n");
        printf("RESULT: 0/%d passed\n", total);
        apr_terminate();
        return 1;
    }

    /* 1/2: version API must return the compiled version string. */
    vstring = apreq_version_string();
    if (vstring != NULL && strcmp(vstring, APREQ_VERSION_STRING) == 0) {
        printf("[1/2] version_string (%s): PASS\n", vstring);
        passed++;
    } else {
        printf("[1/2] version_string: FAIL (got %s)\n", vstring ? vstring : "(null)");
    }

    /* 2/2: cookie header parsing must populate the jar table. */
    jar = apr_table_make(pool, 10);
    if (jar != NULL
        && apreq_parse_cookie_header(pool, jar, "foo=bar; baz=qux") == APR_SUCCESS
        && (val = apr_table_get(jar, "foo")) != NULL
        && strcmp(val, "bar") == 0) {
        printf("[2/2] cookie_parse (foo=bar): PASS\n");
        passed++;
    } else {
        printf("[2/2] cookie_parse: FAIL\n");
    }

    printf("RESULT: %d/%d passed\n", passed, total);
    apr_pool_destroy(pool);
    apr_terminate();
    return (passed == total) ? 0 : 1;
}
