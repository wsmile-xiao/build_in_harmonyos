#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "sqlite3.h"

static int fail(sqlite3 *db, sqlite3_stmt *stmt, const char *where)
{
    fprintf(stderr, "FAIL: %s: %s\n", where, db ? sqlite3_errmsg(db) : "no database");
    if (stmt) {
        sqlite3_finalize(stmt);
    }
    if (db) {
        sqlite3_close(db);
    }
    return 1;
}

int main(void)
{
    sqlite3 *db = NULL;
    sqlite3_stmt *stmt = NULL;
    char *error = NULL;
    int rc = sqlite3_open(":memory:", &db);
    if (rc != SQLITE_OK) {
        return fail(db, NULL, "sqlite3_open");
    }

    rc = sqlite3_exec(db,
        "CREATE TABLE items(id INTEGER PRIMARY KEY, name TEXT);"
        "INSERT INTO items VALUES(1, 'hello');"
        "INSERT INTO items VALUES(2, 'world');",
        NULL, NULL, &error);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "FAIL: setup: %s\n", error ? error : "unknown error");
        sqlite3_free(error);
        sqlite3_close(db);
        return 1;
    }

    rc = sqlite3_prepare_v2(db, "SELECT id, name FROM items ORDER BY id", -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        return fail(db, NULL, "sqlite3_prepare_v2");
    }

    int rows = 0;
    while ((rc = sqlite3_step(stmt)) == SQLITE_ROW) {
        int id = sqlite3_column_int(stmt, 0);
        const char *name = (const char *)sqlite3_column_text(stmt, 1);
        const char *expected = rows == 0 ? "hello" : "world";
        if (id != rows + 1 || !name || strcmp(name, expected) != 0) {
            return fail(db, stmt, "row verification");
        }
        rows++;
    }
    if (rc != SQLITE_DONE || rows != 2) {
        return fail(db, stmt, "sqlite3_step");
    }
    sqlite3_finalize(stmt);

    if (strcmp(sqlite3_libversion(), "3.53.4") != 0) {
        return fail(db, NULL, "sqlite3_libversion");
    }
    sqlite3_close(db);
    printf("sqlite3 3.53.4: OK (CRUD test passed, %d rows)\n", rows);
    return 0;
}
