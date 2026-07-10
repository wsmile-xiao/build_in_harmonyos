#include <stdio.h>
#include <stdlib.h>
#include "sqlite3.h"

int main(void) {
    sqlite3 *db;
    char *err = NULL;
    int rc;

    /* Open in-memory database */
    rc = sqlite3_open(":memory:", &db);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "Cannot open database: %s\n", sqlite3_errmsg(db));
        return 1;
    }

    /* Create table */
    rc = sqlite3_exec(db, "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT, value REAL);", NULL, NULL, &err);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "SQL error: %s\n", err);
        sqlite3_free(err);
        sqlite3_close(db);
        return 1;
    }

    /* Insert */
    rc = sqlite3_exec(db, "INSERT INTO test (name, value) VALUES ('hello', 3.14);", NULL, NULL, &err);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "SQL error: %s\n", err);
        sqlite3_free(err);
        sqlite3_close(db);
        return 1;
    }

    /* Query */
    sqlite3_stmt *stmt;
    rc = sqlite3_prepare_v2(db, "SELECT id, name, value FROM test;", -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "Prepare error: %s\n", sqlite3_errmsg(db));
        sqlite3_close(db);
        return 1;
    }

    while (sqlite3_step(stmt) == SQLITE_ROW) {
        int id = sqlite3_column_int(stmt, 0);
        const unsigned char *name = sqlite3_column_text(stmt, 1);
        double value = sqlite3_column_double(stmt, 2);
        printf("id=%d name=%s value=%.2f\n", id, name, value);
    }

    sqlite3_finalize(stmt);
    sqlite3_close(db);

    printf("test sqlite3 3.49.1: OK\n");
    return 0;
}
