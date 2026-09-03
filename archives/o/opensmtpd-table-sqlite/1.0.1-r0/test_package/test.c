#include <stdio.h>
#include <string.h>
#include <sqlite3.h>

/* Functional test: create an in-memory SQLite database, create a table,
   insert a row, and query it back. This verifies that the sqlite3
   dependency (transitive from opensmtpd-table-sqlite) is correctly
   linked and functional on the target platform. */
int main(void) {
    sqlite3 *db = NULL;
    char *err = NULL;
    int rc;

    rc = sqlite3_open(":memory:", &db);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "FAIL: sqlite3_open: %s\n", sqlite3_errmsg(db));
        return 1;
    }

    rc = sqlite3_exec(db, "CREATE TABLE t(id INTEGER PRIMARY KEY, name TEXT)", NULL, NULL, &err);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "FAIL: CREATE TABLE: %s\n", err ? err : "(null)");
        sqlite3_free(err);
        sqlite3_close(db);
        return 1;
    }

    rc = sqlite3_exec(db, "INSERT INTO t(name) VALUES('test_value')", NULL, NULL, &err);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "FAIL: INSERT: %s\n", err ? err : "(null)");
        sqlite3_free(err);
        sqlite3_close(db);
        return 1;
    }

    sqlite3_stmt *stmt = NULL;
    rc = sqlite3_prepare_v2(db, "SELECT name FROM t WHERE id=1", -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "FAIL: prepare: %s\n", sqlite3_errmsg(db));
        sqlite3_close(db);
        return 1;
    }

    rc = sqlite3_step(stmt);
    if (rc != SQLITE_ROW) {
        fprintf(stderr, "FAIL: step returned %d, expected SQLITE_ROW\n", rc);
        sqlite3_finalize(stmt);
        sqlite3_close(db);
        return 1;
    }

    const unsigned char *name = sqlite3_column_text(stmt, 0);
    if (name == NULL || strcmp((const char *)name, "test_value") != 0) {
        fprintf(stderr, "FAIL: got '%s', expected 'test_value'\n", name ? (const char *)name : "(null)");
        sqlite3_finalize(stmt);
        sqlite3_close(db);
        return 1;
    }

    sqlite3_finalize(stmt);
    sqlite3_close(db);
    printf("PASS: sqlite3 functional test OK\n");
    return 0;
}
