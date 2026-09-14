/*
 * libopendbx test_package consumer test.
 *
 * Verifies the packaged libopendbx on the target platform (HarmonyOS):
 *  1. The sqlite3 backend plugin ships with the package and can be loaded
 *     by path (OpenDBX dynamic backend loading / dlopen).
 *  2. The C API works against a real sqlite3 database file, following the
 *     upstream execution flow odbx_query() -> odbx_result() ->
 *     odbx_result_finish() (the sqlite3 backend executes statements when
 *     odbx_result() is called).
 *  3. Query results (row count, column values) are correct.
 *
 * Usage: opendbx_test <backend_plugin_path> [workdir]
 */
#include <opendbx/api.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int check(int err, odbx_t *h, const char *what)
{
    if (err < 0) {
        fprintf(stderr, "FAIL: %s: %s\n", what, odbx_error(h, err));
        exit(1);
    }
    return err;
}

/* Execute a statement through the upstream query/result/finish pipeline. */
static void exec_stmt(odbx_t *h, const char *sql, const char *what)
{
    odbx_result_t *res = NULL;
    check(odbx_query(h, sql, 0), h, what);
    check(odbx_result(h, &res, NULL, 0), h, what);
    check(odbx_result_finish(res), h, what);
}

int main(int argc, char **argv)
{
    odbx_t *h = NULL;
    odbx_result_t *res = NULL;
    int err;
    unsigned long ncols, i;
    int rows = 0;
    const char *backend = argv[1];
    const char *dbname = "odbx_consumer.sq3";

    if (argc < 2) {
        fprintf(stderr, "usage: opendbx_test <backend_plugin_path>\n");
        return 2;
    }
    if (argc > 2 && chdir(argv[2]) != 0) {
        fprintf(stderr, "FAIL: chdir(%s)\n", argv[2]);
        return 2;
    }

    /* 1. Init with the packaged sqlite3 backend plugin (dynamic loading).
     *    For the sqlite3 backend the "host" is the directory holding the
     *    database file; "./" keeps the DB in the current directory. */
    check(odbx_init(&h, (char *)backend, "./", ""), h, "odbx_init");

    /* 2. Bind to a sqlite3 database file (drop any stale DB from a previous
     *    run so the CREATE TABLE below always starts from a clean file). */
    unlink(dbname);
    check(odbx_bind(h, dbname, "", "", ODBX_BIND_SIMPLE), h, "odbx_bind");

    /* 3. DDL/DML through the C API. */
    exec_stmt(h, "CREATE TABLE t (id INTEGER, name VARCHAR(20))", "CREATE TABLE");
    exec_stmt(h, "INSERT INTO t VALUES (1, 'alpha')", "INSERT 1");
    exec_stmt(h, "INSERT INTO t VALUES (2, 'beta')", "INSERT 2");

    /* 4. Query and iterate rows. */
    check(odbx_query(h, "SELECT * FROM t", 0), h, "SELECT * FROM t");
    check(odbx_result(h, &res, NULL, 0), h, "odbx_result");
    ncols = odbx_column_count(res);
    if (ncols != 2) {
        fprintf(stderr, "FAIL: expected 2 columns, got %lu\n", ncols);
        return 1;
    }
    while ((err = odbx_row_fetch(res)) != ODBX_ROW_DONE) {
        check(err, h, "odbx_row_fetch");
        rows++;
        for (i = 0; i < ncols; i++) {
            const char *name = odbx_column_name(res, i);
            const char *value = odbx_field_value(res, i);
            if (name == NULL || value == NULL) {
                fprintf(stderr, "FAIL: NULL column %lu name/value\n", i);
                return 1;
            }
        }
    }
    check(odbx_result_finish(res), h, "odbx_result_finish");
    if (rows != 2) {
        fprintf(stderr, "FAIL: expected 2 rows, got %d\n", rows);
        return 1;
    }

    /* 5. Verify a specific value. */
    check(odbx_query(h, "SELECT name FROM t WHERE id = 1", 0), h, "SELECT name");
    check(odbx_result(h, &res, NULL, 0), h, "odbx_result 2");
    check(odbx_row_fetch(res), h, "odbx_row_fetch 2");
    if (strcmp(odbx_field_value(res, 0), "alpha") != 0) {
        fprintf(stderr, "FAIL: expected 'alpha', got '%s'\n",
                odbx_field_value(res, 0));
        return 1;
    }
    check(odbx_result_finish(res), h, "odbx_result_finish 2");

    check(odbx_finish(h), h, "odbx_finish");
    printf("PASS: libopendbx consumer test (2 rows, values verified)\n");
    return 0;
}
