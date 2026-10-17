/* Consumer test for routino 3.4.3.
 *
 * Exercises the installed libroutino through its real public C API and
 * prints HMBS_TEST_PACKAGE_RESULT with counters owned by this binary
 * (no stdout scraping). Exit 0 only when every check passes.
 *
 * Cases:
 *   1. Routino_CheckAPIVersion() returns ROUTINO_ERROR_NONE (header/LIB ABI
 *      match; the macro takes no arguments and returns 0 on success).
 *   2. Routino_LoadDatabase() with a nonexistent dir returns NULL and sets
 *      Routino_errno to ROUTINO_ERROR_NO_DATABASE_FILES (11); needs no data.
 *   3. Error/option constants are sane (ROUTINO_ERROR_NONE == 0).
 */
#include <stdio.h>
#include <string.h>

#include <routino.h>

static int checks_run = 0;
static int checks_failed = 0;

#define CHECK(cond) \
    do { \
        ++checks_run; \
        if (!(cond)) { \
            ++checks_failed; \
            printf("CHECK FAILED line %d: %s\n", __LINE__, #cond); \
        } \
    } while (0)

int main(void) {
    const int cases_total = 3;
    int cases_passed = 0;
    int before;

    /* Case 1: API version matches the linked library. */
    before = checks_failed;
    {
        int rc = Routino_CheckAPIVersion();
        printf("Routino_CheckAPIVersion() = %d (ROUTINO_API_VERSION=%d)\n", rc, ROUTINO_API_VERSION);
        CHECK(rc == ROUTINO_ERROR_NONE);
        CHECK(ROUTINO_API_VERSION == 8);
    }
    if (checks_failed == before) ++cases_passed;

    /* Case 2: loading a nonexistent database fails cleanly. */
    before = checks_failed;
    {
        Routino_errno = ROUTINO_ERROR_NONE;
        Routino_Database *db = Routino_LoadDatabase("/nonexistent-routino-db-xyz", "test");
        printf("Routino_LoadDatabase(nonexistent) = %p, Routino_errno=%d\n",
               (void *)db, Routino_errno);
        CHECK(db == NULL);
        CHECK(Routino_errno == ROUTINO_ERROR_NO_DATABASE_FILES);
        if (db) Routino_UnloadDatabase(db);
    }
    if (checks_failed == before) ++cases_passed;

    /* Case 3: public constants are sane. */
    before = checks_failed;
    {
        CHECK(ROUTINO_ERROR_NONE == 0);
        CHECK(ROUTINO_ROUTE_SHORTEST == 0);
        CHECK(ROUTINO_ROUTE_QUICKEST == 1);
        CHECK(ROUTINO_ERROR_NO_DATABASE_FILES == 11);
    }
    if (checks_failed == before) ++cases_passed;

    printf("Results: %d/%d consumer cases passed (%d/%d assertions)\n",
           cases_passed, cases_total,
           checks_run - checks_failed, checks_run);
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,"
           "\"command\":\"./test_routino\",\"discovered\":%d,\"passedCount\":%d}\n",
           cases_passed == cases_total ? "true" : "false",
           cases_total, cases_passed);
    return cases_passed == cases_total ? 0 : 1;
}
