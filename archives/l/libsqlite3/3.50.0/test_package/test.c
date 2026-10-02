#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "sqlite3.h"

/* Consumer end-to-end tests for libsqlite3 on HarmonyOS PC (aarch64).
 *
 * Case 1 (e2e persistence CRUD lifecycle): file-backed DB, schema, batched
 *        inserts, prepared query, transaction rollback, update, delete,
 *        close/reopen and re-verify persistence.
 * Case 2 (e2e query engine paths): aggregate + JOIN + index + FTS5 + RTREE
 *        exercised through the exported C API the way an application uses it.
 * Case 3 (e2e metadata/version contract): version string and compile-option
 *        introspection used by consumers for feature detection.
 */

static int checks = 0;
static int failures = 0;

static void ok(int cond, const char *what)
{
    checks++;
    if (!cond) {
        failures++;
        fprintf(stderr, "FAIL: %s\n", what);
    } else {
        printf("  ok %02d: %s\n", checks, what);
    }
}

static int exec_sql(sqlite3 *db, const char *sql, const char *what)
{
    char *error = NULL;
    int rc = sqlite3_exec(db, sql, NULL, NULL, &error);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "FAIL: %s: %s\n", what, error ? error : sqlite3_errmsg(db));
        sqlite3_free(error);
        failures++;
        checks++;
        return 0;
    }
    checks++;
    printf("  ok %02d: %s\n", checks, what);
    return 1;
}

static int scalar_int(sqlite3 *db, const char *sql, const char *what)
{
    sqlite3_stmt *stmt = NULL;
    int value = -1000000;
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) != SQLITE_OK) {
        fprintf(stderr, "FAIL: %s (prepare): %s\n", what, sqlite3_errmsg(db));
        failures++;
        checks++;
        return value;
    }
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        value = sqlite3_column_int(stmt, 0);
    }
    sqlite3_finalize(stmt);
    return value;
}

/* Case 1: full CRUD lifecycle with real persistence on disk. */
static void case1_persistence_lifecycle(const char *path)
{
    sqlite3 *db = NULL;
    sqlite3_stmt *stmt = NULL;
    printf("case1: persistence CRUD lifecycle (%s)\n", path);
    remove(path);
    if (sqlite3_open(path, &db) != SQLITE_OK) {
        fprintf(stderr, "FAIL: case1 open\n");
        failures++;
        return;
    }
    exec_sql(db,
        "PRAGMA journal_mode=WAL;"
        "CREATE TABLE items(id INTEGER PRIMARY KEY, name TEXT NOT NULL, qty INT);"
        "CREATE INDEX idx_items_name ON items(name);",
        "case1 schema+index created");
    exec_sql(db,
        "INSERT INTO items(name, qty) VALUES('alpha', 10), ('beta', 20), ('gamma', 30);",
        "case1 batch insert 3 rows");

    if (sqlite3_prepare_v2(db,
            "SELECT name, qty FROM items WHERE name = ?1", -1, &stmt, NULL) == SQLITE_OK) {
        sqlite3_bind_text(stmt, 1, "beta", -1, SQLITE_STATIC);
        ok(sqlite3_step(stmt) == SQLITE_ROW && sqlite3_column_int(stmt, 1) == 20,
           "case1 prepared statement with bound parameter");
        sqlite3_finalize(stmt);
    } else {
        ok(0, "case1 prepared statement with bound parameter (prepare)");
    }

    exec_sql(db, "BEGIN; UPDATE items SET qty = 99 WHERE name = 'gamma'; ROLLBACK;",
        "case1 transaction rollback executed");
    ok(scalar_int(db, "SELECT qty FROM items WHERE name='gamma'", "case1 rollback read") == 30,
       "case1 rollback restored qty=30");

    exec_sql(db, "BEGIN; DELETE FROM items WHERE name='alpha'; COMMIT;",
        "case1 delete in transaction");
    ok(scalar_int(db, "SELECT COUNT(*) FROM items", "case1 count after delete") == 2,
       "case1 row count is 2 after delete");

    sqlite3_close(db);
    db = NULL;

    /* Reopen: prove durability across close/reopen like a real application. */
    if (sqlite3_open(path, &db) != SQLITE_OK) {
        fprintf(stderr, "FAIL: case1 reopen\n");
        failures++;
        return;
    }
    ok(scalar_int(db, "SELECT COUNT(*) FROM items WHERE qty=20", "case1 reopen count") == 1,
       "case1 data survives close/reopen (durable)");
    ok(scalar_int(db, "SELECT qty FROM items WHERE name='gamma'", "case1 reopen value") == 30,
       "case1 rollback state survives close/reopen");
    exec_sql(db, "PRAGMA integrity_check", "case1 integrity_check ran");
    sqlite3_close(db);
}

/* Case 2: query-engine paths through the exported API (join, aggregate, fts5, rtree). */
static void case2_query_engine(void)
{
    sqlite3 *db = NULL;
    printf("case2: query engine paths\n");
    if (sqlite3_open(":memory:", &db) != SQLITE_OK) {
        fprintf(stderr, "FAIL: case2 open\n");
        failures++;
        return;
    }
    exec_sql(db,
        "CREATE TABLE cust(id INTEGER PRIMARY KEY, name TEXT);"
        "CREATE TABLE orders(id INTEGER PRIMARY KEY, cust INT, amount INT);"
        "INSERT INTO cust VALUES(1,'ann'),(2,'bob');"
        "INSERT INTO orders VALUES(1,1,100),(2,1,50),(3,2,70);",
        "case2 schema+data");
    ok(scalar_int(db,
        "SELECT SUM(o.amount) FROM orders o JOIN cust c ON c.id=o.cust WHERE c.name='ann'",
        "case2 join+aggregate read") == 150,
       "case2 JOIN + SUM returns 150");
    ok(scalar_int(db, "SELECT COUNT(*) FROM orders WHERE amount > 60", "case2 filter read") == 2,
       "case2 range filter returns 2");

    exec_sql(db,
        "CREATE VIRTUAL TABLE ft USING fts5(body);"
        "INSERT INTO ft VALUES('harmony open source database');"
        "INSERT INTO ft VALUES('unrelated text');",
        "case2 fts5 virtual table populated");
    ok(scalar_int(db, "SELECT COUNT(*) FROM ft WHERE ft MATCH 'database'", "case2 fts5 match read") == 1,
       "case2 FTS5 full-text MATCH returns 1");

    exec_sql(db,
        "CREATE VIRTUAL TABLE r USING rtree(id, minX, maxX, minY, maxY);"
        "INSERT INTO r VALUES(1, 0, 10, 0, 10);"
        "INSERT INTO r VALUES(2, 100, 110, 100, 110);",
        "case2 rtree virtual table populated");
    ok(scalar_int(db, "SELECT COUNT(*) FROM r WHERE minX <= 5 AND maxX >= 5", "case2 rtree read") == 1,
       "case2 RTREE spatial query returns 1");
    sqlite3_close(db);
}

/* Case 3: version / compile-option contract used by consumers. */
static void case3_metadata(void)
{
    sqlite3 *db = NULL;
    sqlite3_stmt *stmt = NULL;
    int seen_fts5 = 0, seen_rtree = 0, seen_threadsafe = 0, options = 0;
    printf("case3: version and compile-option metadata\n");
    ok(strcmp(sqlite3_libversion(), "3.50.0") == 0, "case3 sqlite3_libversion() == 3.50.0");
    ok(sqlite3_libversion_number() == 3050000, "case3 sqlite3_libversion_number() == 3050000");
    ok(sqlite3_threadsafe() == 1, "case3 sqlite3_threadsafe() == 1");

    if (sqlite3_open(":memory:", &db) != SQLITE_OK) {
        fprintf(stderr, "FAIL: case3 open\n");
        failures++;
        return;
    }
    if (sqlite3_prepare_v2(db, "PRAGMA compile_options", -1, &stmt, NULL) == SQLITE_OK) {
        while (sqlite3_step(stmt) == SQLITE_ROW) {
            const char *opt = (const char *)sqlite3_column_text(stmt, 0);
            options++;
            if (opt && strstr(opt, "ENABLE_FTS5")) seen_fts5 = 1;
            if (opt && strstr(opt, "ENABLE_RTREE")) seen_rtree = 1;
            if (opt && strstr(opt, "THREADSAFE")) seen_threadsafe = 1;
        }
        sqlite3_finalize(stmt);
    }
    ok(options > 0, "case3 compile_options enumerates entries");
    ok(seen_fts5, "case3 compile_options contains ENABLE_FTS5");
    ok(seen_rtree, "case3 compile_options contains ENABLE_RTREE");
    ok(seen_threadsafe, "case3 compile_options contains THREADSAFE");
    sqlite3_close(db);
}

int main(void)
{
    const char *path = "e2e_consumer.db";
    printf("libsqlite3 3.50.0 consumer e2e suite (OHOS PC)\n");
    case1_persistence_lifecycle(path);
    case2_query_engine();
    case3_metadata();
    remove(path);
    remove("e2e_consumer.db-wal");
    remove("e2e_consumer.db-shm");
    printf("RESULT: %d checks, %d failures\n", checks, failures);
    if (failures) {
        printf("libsqlite3 3.50.0: FAILED\n");
        return 1;
    }
    printf("libsqlite3 3.50.0: OK (3 consumer e2e cases passed)\n");
    return 0;
}
