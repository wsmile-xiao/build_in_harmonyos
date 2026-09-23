/*
 * Consumer test for sqlean: loads the math and crypto SQLite extensions
 * from the installed package and asserts real query results.
 */
#include <sqlite3.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;

static void expect(sqlite3 *db, const char *sql, const char *want) {
    sqlite3_stmt *stmt = NULL;
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) != SQLITE_OK) {
        fprintf(stderr, "prepare failed: %s\n  => %s\n", sql, sqlite3_errmsg(db));
        failures++;
        return;
    }
    if (sqlite3_step(stmt) != SQLITE_ROW) {
        fprintf(stderr, "no row: %s\n  => %s\n", sql, sqlite3_errmsg(db));
        failures++;
        sqlite3_finalize(stmt);
        return;
    }
    const unsigned char *got = sqlite3_column_text(stmt, 0);
    if (got == NULL || strcmp((const char *)got, want) != 0) {
        fprintf(stderr, "mismatch: %s\n  => got '%s', want '%s'\n", sql,
                got ? (const char *)got : "(null)", want);
        failures++;
    }
    sqlite3_finalize(stmt);
}

static void load_ext(sqlite3 *db, const char *dir, const char *name) {
    char path[1024];
    char *err = NULL;
    snprintf(path, sizeof path, "%s/%s", dir, name);
    if (sqlite3_load_extension(db, path, NULL, &err) != SQLITE_OK) {
        fprintf(stderr, "cannot load extension %s: %s\n", path,
                err ? err : "unknown error");
        exit(1);
    }
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <sqlean-extension-dir>\n", argv[0]);
        return 2;
    }
    sqlite3 *db = NULL;
    if (sqlite3_open(":memory:", &db) != SQLITE_OK) {
        fprintf(stderr, "cannot open in-memory database\n");
        return 1;
    }
    if (sqlite3_enable_load_extension(db, 1) != SQLITE_OK) {
        fprintf(stderr, "cannot enable extension loading\n");
        return 1;
    }

    load_ext(db, argv[1], "math");
    load_ext(db, argv[1], "crypto");

    expect(db, "select math_ceil(3.3) = 4", "1");
    expect(db, "select math_floor(-3.9) = -4", "1");
    expect(db, "select math_trunc(-3.3) = -3", "1");
    expect(db, "select lower(hex(sha1('abc'))) "
               "= 'a9993e364706816aba3e25717850c26c9cd0d89d'", "1");
    expect(db, "select lower(hex(sha256(''))) "
               "= 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'",
           "1");

    sqlite3_close(db);
    if (failures > 0) {
        fprintf(stderr, "test_sqlean: %d assertion(s) failed\n", failures);
        return 1;
    }
    printf("test_sqlean: all assertions passed\n");
    return 0;
}
