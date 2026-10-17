/* test_package for sqlite-vec — basic vector search test.
 *
 * Creates a vec0 virtual table, inserts vectors, runs KNN search,
 * and verifies results.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sqlite3.h"
#include "sqlite-vec.h"

int main(void) {
    sqlite3 *db;
    char *err = NULL;
    int rc;

    rc = sqlite3_open(":memory:", &db);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "Cannot open database: %s\n", sqlite3_errmsg(db));
        return 1;
    }

    /* Register the vec0 extension */
    rc = sqlite3_vec_init(db, &err, NULL);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "Cannot init sqlite-vec: %s\n", err ? err : "(null)");
        sqlite3_free(err);
        sqlite3_close(db);
        return 1;
    }

    /* Check version */
    sqlite3_stmt *stmt;
    rc = sqlite3_prepare_v2(db, "SELECT vec_version()", -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "Prepare failed: %s\n", sqlite3_errmsg(db));
        sqlite3_close(db);
        return 1;
    }
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        printf("sqlite-vec version: %s\n", sqlite3_column_text(stmt, 0));
    }
    sqlite3_finalize(stmt);

    /* Create virtual table and insert vectors */
    const char *sql =
        "CREATE VIRTUAL TABLE v USING vec0(vector float[1]);"
        "INSERT INTO v(rowid, vector) VALUES (1, '[1]');"
        "INSERT INTO v(rowid, vector) VALUES (2, '[2]');"
        "INSERT INTO v(rowid, vector) VALUES (3, '[3]');";
    rc = sqlite3_exec(db, sql, NULL, NULL, &err);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "SQL error: %s\n", err);
        sqlite3_free(err);
        sqlite3_close(db);
        return 1;
    }

    /* KNN search: find nearest vectors to [0] */
    rc = sqlite3_prepare_v2(db,
        "SELECT rowid, distance FROM v WHERE vector MATCH '[0]' AND k = 3",
        -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "KNN prepare failed: %s\n", sqlite3_errmsg(db));
        sqlite3_close(db);
        return 1;
    }

    int count = 0;
    int rowids[3];
    double distances[3];
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        rowids[count] = sqlite3_column_int(stmt, 0);
        distances[count] = sqlite3_column_double(stmt, 1);
        printf("  rowid=%d distance=%f\n", rowids[count], distances[count]);
        count++;
    }
    sqlite3_finalize(stmt);

    /* Verify results */
    if (count != 3) {
        fprintf(stderr, "FAIL: expected 3 results, got %d\n", count);
        sqlite3_close(db);
        return 1;
    }
    if (rowids[0] != 1 || rowids[1] != 2 || rowids[2] != 3) {
        fprintf(stderr, "FAIL: unexpected rowid order\n");
        sqlite3_close(db);
        return 1;
    }
    if (distances[0] != 1.0 || distances[1] != 2.0 || distances[2] != 3.0) {
        fprintf(stderr, "FAIL: unexpected distances\n");
        sqlite3_close(db);
        return 1;
    }

    printf("All tests passed!\n");
    sqlite3_close(db);
    return 0;
}
