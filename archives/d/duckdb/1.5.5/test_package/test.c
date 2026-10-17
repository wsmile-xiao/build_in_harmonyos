/* DuckDB 1.5.5 L1 consumer test (C API).
 *
 * Truthfully exercises the shipped library through the public C API:
 *   1. duckdb_open(NULL)      -> in-memory database
 *   2. duckdb_connect         -> connection
 *   3. SELECT 1 + 1           -> scalar result
 *   4. CREATE TABLE           -> DDL
 *   5. INSERT (multi-row)     -> DML
 *   6. SELECT COUNT(*)        -> verify written rows are readable
 *   7. SELECT with VARCHAR    -> verify string round-trip
 *
 * Any failed step prints the DuckDB error string and returns non-zero, so a
 * passing run is real evidence that the library links and executes correctly
 * on the HarmonyOS PC (aarch64) target.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "duckdb.h"

static int fail(const char *stage, duckdb_result *res) {
    fprintf(stderr, "[test_duckdb] FAIL at %s: %s\n", stage,
            res ? duckdb_result_error(res) : "(no result)");
    if (res) duckdb_destroy_result(res);
    return 1;
}

int main(void) {
    duckdb_database db = NULL;
    duckdb_connection con = NULL;
    duckdb_result res;
    int64_t val;
    int rc = 1;

    if (duckdb_open(NULL, &db) != DuckDBSuccess) {
        fprintf(stderr, "[test_duckdb] FAIL: duckdb_open\n");
        return 1;
    }
    if (duckdb_connect(db, &con) != DuckDBSuccess) {
        fprintf(stderr, "[test_duckdb] FAIL: duckdb_connect\n");
        duckdb_close(&db);
        return 1;
    }

    /* 1. scalar expression */
    if (duckdb_query(con, "SELECT 1 + 1 AS result", &res) != DuckDBSuccess) {
        rc = fail("SELECT 1+1", &res);
        goto done;
    }
    val = duckdb_value_int64(&res, 0, 0);
    duckdb_destroy_result(&res);
    if (val != 2) {
        fprintf(stderr, "[test_duckdb] FAIL: SELECT 1+1 = %lld, expected 2\n",
                (long long)val);
        goto done;
    }

    /* 2. DDL */
    if (duckdb_query(con,
                     "CREATE TABLE t(id INTEGER, name VARCHAR)",
                     &res) != DuckDBSuccess) {
        rc = fail("CREATE TABLE", &res);
        goto done;
    }
    duckdb_destroy_result(&res);

    /* 3. DML */
    if (duckdb_query(con,
                     "INSERT INTO t VALUES (1, 'hello'), (2, 'world')",
                     &res) != DuckDBSuccess) {
        rc = fail("INSERT", &res);
        goto done;
    }
    duckdb_destroy_result(&res);

    /* 4. aggregate read-back */
    if (duckdb_query(con, "SELECT COUNT(*) FROM t", &res) != DuckDBSuccess) {
        rc = fail("SELECT COUNT(*)", &res);
        goto done;
    }
    val = duckdb_value_int64(&res, 0, 0);
    duckdb_destroy_result(&res);
    if (val != 2) {
        fprintf(stderr, "[test_duckdb] FAIL: COUNT(*) = %lld, expected 2\n",
                (long long)val);
        goto done;
    }

    /* 5. string round-trip */
    if (duckdb_query(con,
                     "SELECT name FROM t WHERE id = 2", &res) != DuckDBSuccess) {
        rc = fail("SELECT name WHERE id=2", &res);
        goto done;
    }
    {
        const char *name = duckdb_value_varchar(&res, 0, 0);
        if (name == NULL || strcmp(name, "world") != 0) {
            fprintf(stderr, "[test_duckdb] FAIL: name = '%s', expected 'world'\n",
                    name ? name : "(null)");
            duckdb_free((void *)name);
            duckdb_destroy_result(&res);
            goto done;
        }
        duckdb_free((void *)name);
    }
    duckdb_destroy_result(&res);

    printf("[test_duckdb] PASS: duckdb %s — open/connect/DDL/DML/SELECT OK\n",
           duckdb_library_version());
    rc = 0;

done:
    duckdb_disconnect(&con);
    duckdb_close(&db);
    return rc;
}
