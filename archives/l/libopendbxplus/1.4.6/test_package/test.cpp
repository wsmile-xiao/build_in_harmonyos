/*
 * libopendbxplus test_package consumer test (C++ API).
 *
 * Verifies the packaged libopendbxplus on the target platform (HarmonyOS):
 *  1. The C++ wrapper links against the packaged libopendbx and the sqlite3
 *     backend plugin loads by path (dynamic backend loading / dlopen).
 *  2. The C++ API (OpenDBX::Conn / Stmt / Result) works against a real
 *     sqlite3 database file.
 *  3. Query results (row count, column values) are correct.
 *
 * Usage: opendbxplus_test <backend_plugin_path> [workdir]
 */
#include <opendbx/api>

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <unistd.h>

using namespace OpenDBX;

static void die(const char *what, const std::exception &e)
{
    std::fprintf(stderr, "FAIL: %s: %s\n", what, e.what());
    std::exit(1);
}

/* Execute a statement and drain its result set to ODBX_RES_DONE. */
static void exec_stmt(Conn &conn, const char *sql)
{
    Stmt stmt = conn.create(sql);
    Result result = stmt.execute();
    while (result.getResult() != ODBX_RES_DONE) {
    }
    result.finish();
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        std::fprintf(stderr, "usage: opendbxplus_test <backend_plugin_path>\n");
        return 2;
    }
    if (argc > 2 && chdir(argv[2]) != 0) {
        std::fprintf(stderr, "FAIL: chdir(%s)\n", argv[2]);
        return 2;
    }

    try {
        /* All Stmt/Result objects are kept inside this block: the C++ wrapper
         * stores a raw handle in their implementations, so every result set
         * must be out of scope before the connection is torn down. The Conn
         * destructor then unbinds and finishes the connection. */
        {
            /* 1. Connect through the packaged sqlite3 backend plugin. For the
             *    sqlite3 backend the "host" is the directory holding the
             *    database file; "./" keeps the DB in the current directory. */
            Conn conn(argv[1], "./", "");
            /* Drop any stale DB from a previous run so the CREATE TABLE below
             * always starts from a clean file. */
            unlink("odbx_consumer_plus.sq3");
            conn.bind("odbx_consumer_plus.sq3", "", "", ODBX_BIND_SIMPLE);

            /* 2. DDL/DML through the C++ API (drained to ODBX_RES_DONE). */
            exec_stmt(conn, "CREATE TABLE t (id INTEGER, name VARCHAR(20))");
            exec_stmt(conn, "INSERT INTO t VALUES (1, 'alpha')");
            exec_stmt(conn, "INSERT INTO t VALUES (2, 'beta')");

            /* 3. Query and iterate rows. */
            Stmt stmt4 = conn.create("SELECT * FROM t");
            Result res4 = stmt4.execute();
            int rows = 0;
            odbxres stat;
            while ((stat = res4.getResult()) != ODBX_RES_DONE) {
                if (stat == ODBX_RES_TIMEOUT) {
                    std::fprintf(stderr, "FAIL: result timeout\n");
                    return 1;
                }
                if (stat == ODBX_RES_NOROWS) {
                    continue;
                }
                unsigned long fields = res4.columnCount();
                while (res4.getRow() != ODBX_ROW_DONE) {
                    rows++;
                    for (unsigned long i = 0; i < fields; i++) {
                        if (res4.fieldValue(i) == NULL) {
                            std::fprintf(stderr, "FAIL: NULL field %lu\n", i);
                            return 1;
                        }
                    }
                }
            }
            res4.finish();
            if (rows != 2) {
                std::fprintf(stderr, "FAIL: expected 2 rows, got %d\n", rows);
                return 1;
            }

            /* 4. Verify a specific value. */
            Stmt stmt5 = conn.create("SELECT name FROM t WHERE id = 1");
            Result res5 = stmt5.execute();
            if (res5.getResult() == ODBX_RES_ROWS &&
                res5.getRow() != ODBX_ROW_DONE) {
                const char *value = res5.fieldValue(0);
                if (value == NULL || std::strcmp(value, "alpha") != 0) {
                    std::fprintf(stderr, "FAIL: expected 'alpha', got '%s'\n",
                                 value ? value : "(null)");
                    return 1;
                }
            } else {
                std::fprintf(stderr, "FAIL: no row returned for WHERE id = 1\n");
                return 1;
            }
            while (res5.getResult() != ODBX_RES_DONE) {
            }
            res5.finish();
        }
        std::printf("PASS: libopendbxplus consumer test (2 rows, values verified)\n");
    } catch (const Exception &e) {
        die("OpenDBX C++ API", e);
    } catch (const std::exception &e) {
        die("std::exception", e);
    }
    return 0;
}
