/* Consumer test for the openmama package: the resource pool URI parser.
 *
 * mamaResourcePoolUri_parse() is the local stand-in for APR-util's
 * apr_uri_parse (APR-util is not published for this platform, see notes.md).
 * The resource pool splits "<scheme>://<authority>/<path>?<query>" URIs with
 * it, and both call sites - mamaResourcePool_createTransportFromUri() in C and
 * MamaResourcePool::createSubscriptionFromUri() in C++ - depend on the path
 * and the query it reports, so the documented apr_uri_parse alignment is
 * checked here for every URI form the resource pool documents.
 *
 * Every check increments the failure counter, main() returns it, and the
 * test_package conanfile relies on the exit status.
 */
#include <stdio.h>
#include <string.h>

#include <apr_pools.h>

/* Declaration of the resource pool URI parser under test.
 *
 * mamaResourcePoolUri_parse() is the local replacement for APR-util's
 * apr_uri_parse; its declaration lives in the resource pool's internal header
 * (mama/c_cpp/src/c/resourcepool.h), which is not installed because it is not
 * part of the public API - the parser is reached by consumers through
 * mamaResourcePool_createSubscriptionFromUri() and its C++ counterpart. Since
 * that path needs a middleware bridge this package does not ship yet (see
 * notes.md), the consumer side repeats the prototype and the member layout
 * here and checks the parsing contract directly.
 */
typedef struct mamaResourcePoolUri_
{
    char* mScheme;    /* e.g. "mama"      - NULL when absent    */
    char* mAuthority; /* e.g. "transport" - NULL when absent    */
    char* mPath;      /* leading '/', "" when absent            */
    char* mQuery;     /* e.g. "a=1"       - NULL when absent    */
} mamaResourcePoolUri;

extern int
mamaResourcePoolUri_parse (apr_pool_t* pool, const char* uri,
                           mamaResourcePoolUri* parsed);

static int failures = 0;

static void
check (int condition, const char* what)
{
    printf ("  [%s] %s\n", condition ? "ok" : "FAIL", what);
    if (!condition)
    {
        failures++;
    }
}

static int
same (const char* actual, const char* expected)
{
    if (NULL == expected)
    {
        return NULL == actual;
    }
    return NULL != actual && 0 == strcmp (actual, expected);
}

static void
check_uri (apr_pool_t* pool,
           const char* uri,
           const char* scheme,
           const char* authority,
           const char* path,
           const char* query)
{
    mamaResourcePoolUri parsed;
    char what[256];
    int rc = mamaResourcePoolUri_parse (pool, uri, &parsed);

    snprintf (what, sizeof (what), "%s -> scheme=%s authority=%s path=%s query=%s",
              uri,
              scheme ? scheme : "()",
              authority ? authority : "()",
              path ? path : "()",
              query ? query : "()");

    check (0 == rc
           && same (parsed.mScheme, scheme)
           && same (parsed.mAuthority, authority)
           && same (parsed.mPath, path)
           && same (parsed.mQuery, query), what);
}

int
main (void)
{
    apr_pool_t* pool = NULL;

    printf ("openmama consumer test (resource pool URI parser)\n");

    /* APR must be initialised before any pool is created. */
    apr_initialize ();
    if (APR_SUCCESS != apr_pool_create (&pool, NULL))
    {
        printf ("  [FAIL] apr_pool_create() failed\n");
        return 1;
    }

    /* The form upstream documents and uses throughout the examples. */
    check_uri (pool, "mama://transport/source/topic",
               "mama", "transport", "/source/topic", NULL);

    /* Query directly after the path. */
    check_uri (pool, "mama://transport/topic?option=value",
               "mama", "transport", "/topic", "option=value");

    /* Query directly after the authority: no path, the query must survive. */
    check_uri (pool, "mama://transport?option=value",
               "mama", "transport", "", "option=value");

    /* Empty authority (three slashes). */
    check_uri (pool, "mama:///topic", "mama", "", "/topic", NULL);

    /* No authority at all. */
    check_uri (pool, "mama:/topic", "mama", NULL, "/topic", NULL);

    /* Path with a trailing separator. */
    check_uri (pool, "mama://transport/", "mama", "transport", "/", NULL);

    /* Fragment is not part of the resource pool URI. */
    check_uri (pool, "mama://transport/source/topic?option=value#fragment",
               "mama", "transport", "/source/topic", "option=value");

    /* Scheme names are case insensitive, the rest is not. */
    check_uri (pool, "MAMA://Transport/Topic",
               "mama", "Transport", "/Topic", NULL);

    /* A URI without a scheme is rejected. */
    check (0 != mamaResourcePoolUri_parse (pool, "transport/topic", NULL),
           "missing scheme is rejected");
    check (0 != mamaResourcePoolUri_parse (NULL, "mama://transport", NULL),
           " arguments are rejected");

    apr_pool_destroy (pool);
    apr_terminate ();
    printf ("%s: %d check(s) failed\n", failures ? "FAILURE" : "SUCCESS", failures);
    return failures;
}
