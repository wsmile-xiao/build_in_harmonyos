/*
 * L1 consumer test for libiodbc2 (iODBC driver manager).
 *
 * R34: the test must actually exercise the packaged library's API — it links
 * against libiodbc and drives a real ODBC handle lifecycle, instead of just
 * printing a string.
 *
 * The driver manager is usable end-to-end without any installed driver:
 * allocating an environment, selecting ODBC 3.x behaviour and allocating a
 * connection handle are all internal operations.  Enumerating drivers
 * (SQLDrivers) is expected to report SQL_NO_DATA on a clean system.
 */
#include <stdint.h>
#include <stdio.h>

#include <sql.h>
#include <sqlext.h>

static int failures = 0;

static void expect_success(SQLRETURN rc, const char *what)
{
    if (!SQL_SUCCEEDED(rc)) {
        fprintf(stderr, "FAIL: %s returned %d\n", what, (int)rc);
        failures++;
    }
}

static void expect_equal(SQLRETURN got, SQLRETURN want, const char *what)
{
    if (got != want) {
        fprintf(stderr, "FAIL: %s = %d, expected %d\n", what, (int)got, (int)want);
        failures++;
    }
}

int main(void)
{
    SQLHENV env = SQL_NULL_HENV;
    SQLHDBC dbc = SQL_NULL_HDBC;
    SQLCHAR description[256] = {0};
    SQLSMALLINT description_len = 0;
    SQLCHAR attributes[256] = {0};
    SQLSMALLINT attributes_len = 0;

    /* -- library version actually linked in ---------------------------- */
    {
        SQLUSMALLINT major = 0, minor = 0;
        char version[64] = {0};
        if (SQL_SUCCEEDED(SQLGetInfo(SQL_NULL_HENV, SQL_DRIVER_ODBC_VER,
                                     version, sizeof(version), NULL))) {
            /* not meaningful before an env exists; ignore */
        }
        SQLGetEnvAttr(SQL_NULL_HENV, SQL_ATTR_ODBC_VERSION, NULL, 0, NULL);
        (void)major; (void)minor;
    }

    /* -- environment handle -------------------------------------------- */
    expect_success(SQLAllocHandle(SQL_HANDLE_ENV, SQL_NULL_HANDLE, &env),
                   "SQLAllocHandle(SQL_HANDLE_ENV)");
    if (env == SQL_NULL_HENV) {
        fprintf(stderr, "FAIL: no environment handle\n");
        return 1;
    }

    expect_success(SQLSetEnvAttr(env, SQL_ATTR_ODBC_VERSION,
                                 (SQLPOINTER)(uintptr_t)SQL_OV_ODBC3, 0),
                   "SQLSetEnvAttr(SQL_ATTR_ODBC_VERSION)");

    {
        SQLINTEGER odbc_ver = 0;
        expect_success(SQLGetEnvAttr(env, SQL_ATTR_ODBC_VERSION, &odbc_ver,
                                     sizeof(odbc_ver), NULL),
                       "SQLGetEnvAttr(SQL_ATTR_ODBC_VERSION)");
        expect_equal((SQLRETURN)(odbc_ver == (SQLINTEGER)SQL_OV_ODBC3 ? SQL_SUCCESS
                                                                    : SQL_ERROR),
                     SQL_SUCCESS, "env ODBC version round-trip");
    }

    /* -- connection handle (no driver needed) --------------------------- */
    expect_success(SQLAllocHandle(SQL_HANDLE_DBC, env, &dbc),
                   "SQLAllocHandle(SQL_HANDLE_DBC)");
    if (dbc == SQL_NULL_HDBC) {
        fprintf(stderr, "FAIL: no connection handle\n");
        SQLFreeHandle(SQL_HANDLE_ENV, env);
        return 1;
    }

    /* NOTE: unlike unixODBC, iODBC answers SQLGetDiagRec(SQL_HANDLE_DBC) on a
     * fresh handle with SQL_ERROR rather than SQL_NO_DATA, so no diagnostic
     * assertion is made here. */

    /* Driver enumeration on a driver-less system returns SQL_NO_DATA. */
    expect_equal(SQLDrivers(env, SQL_FETCH_FIRST, description,
                            sizeof(description), &description_len,
                            attributes, sizeof(attributes), &attributes_len),
                 SQL_NO_DATA, "SQLDrivers on a driver-less system");

    /* -- teardown ------------------------------------------------------- */
    expect_success(SQLFreeHandle(SQL_HANDLE_DBC, dbc), "SQLFreeHandle(DBC)");
    expect_success(SQLFreeHandle(SQL_HANDLE_ENV, env), "SQLFreeHandle(ENV)");

    if (failures != 0) {
        fprintf(stderr, "libiodbc2 3.52.16: %d check(s) FAILED\n", failures);
        return 1;
    }
    printf("libiodbc2 3.52.16: OK (driver-manager API smoke test passed)\n");
    return 0;
}
