#include <stdio.h>
#include <sqlite3.h>

int main(void) {
    sqlite3 *db = NULL;
    sqlite3_stmt *stmt = NULL;
    int result = 1;

    if (sqlite3_open(":memory:", &db) != SQLITE_OK) {
        fprintf(stderr, "sqlite3_open failed: %s\n", db ? sqlite3_errmsg(db) : "no handle");
        goto done;
    }
    if (sqlite3_prepare_v2(db, "SELECT 6 * 7", -1, &stmt, NULL) != SQLITE_OK) {
        fprintf(stderr, "sqlite3_prepare_v2 failed: %s\n", sqlite3_errmsg(db));
        goto done;
    }
    if (sqlite3_step(stmt) != SQLITE_ROW || sqlite3_column_int(stmt, 0) != 42) {
        fprintf(stderr, "unexpected query result\n");
        goto done;
    }

    printf("libSQL SQLite C API %s: in-memory query OK\n", sqlite3_libversion());
    result = 0;

done:
    sqlite3_finalize(stmt);
    if (db) {
        sqlite3_close(db);
    }
    return result;
}
