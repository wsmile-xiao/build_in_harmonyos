/* Upstream sqlite3 file-backend regression subset for OpenDBX 1.4.6.
 *
 * Mirrors the upstream odbxtest sqlite3 path (file database, no server, no
 * credentials -- see OpenDBX/Test_application: odbxtest -b sqlite3backend
 * -h <dir> -d <file>): odbx_init + odbx_bind + CREATE/INSERT/SELECT/DROP
 * through odbx_query/odbx_result, verifying the returned rows and that the
 * backing file was really created on disk (non-empty).
 *
 * Usage: test_upstream_sqlite3 [db_dir] [backend]
 *   db_dir : writable directory for the temp .sq3 file (default ".").
 *   backend: backend NAME for odbx_init (default "sqlite3"). Must be a
 *            name, not a file path: odbx_init dlopens
 *            "lib<name>backend.so" via LD_LIBRARY_PATH and its compiled
 *            LIBPATH, and an absolute path argument gets mangled into
 *            lib<abspath>backend.so (rc=-6). The caller stages
 *            libsqlite3backend.so under its bare soname on
 *            LD_LIBRARY_PATH before invoking.
 */
#include <stdio.h>
#include <string.h>

#include <sys/stat.h>

#include <odbx.h>

static int passed = 0;
static int failed = 0;

#define CHECK(cond, name)                                                     \
    do {                                                                      \
        if (cond) {                                                           \
            printf("PASS: %s\n", name);                                       \
            ++passed;                                                         \
        } else {                                                              \
            printf("FAIL: %s\n", name);                                       \
            ++failed;                                                         \
        }                                                                     \
    } while (0)

/* Run a statement that must not return rows (CREATE/INSERT/DROP): drain all
 * results until ODBX_RES_DONE, fail on ROWS or errors. Adds affected rows. */
static int exec_norows(odbx_t* handle, const char* sql,
                       unsigned long long* affected)
{
    odbx_result_t* result = NULL;
    int rc = odbx_query(handle, sql, 0);
    if (rc != ODBX_ERR_SUCCESS) {
        printf("FAIL: query rc=%d sql=%.50s err=%s\n", rc, sql,
               odbx_error(handle, rc));
        return -1;
    }
    for (;;) {
        result = NULL;
        rc = odbx_result(handle, &result, NULL, 0);
        if (rc == ODBX_RES_DONE) {
            return 0;
        }
        if (rc == ODBX_RES_NOROWS) {
            if (affected != NULL && result != NULL) {
                *affected += odbx_rows_affected(result);
            }
            if (result != NULL) {
                odbx_result_finish(result);
            }
            continue;
        }
        if (result != NULL) {
            odbx_result_finish(result);
        }
        printf("FAIL: unexpected result rc=%d sql=%.50s err=%s\n", rc, sql,
               odbx_error(handle, rc < 0 ? rc : -ODBX_ERR_BACKEND));
        return -1;
    }
}

int main(int argc, char** argv)
{
    const char* rawdir = (argc > 1 && argv[1][0] != '\0') ? argv[1] : ".";
    const char* backend = (argc > 2 && argv[2][0] != '\0') ? argv[2] : "sqlite3";
    char host[1024];
    char dbpath[1152];
    const char* dbfile = "odbx_hmbs_upstream.sq3";
    odbx_t* handle = NULL;
    odbx_result_t* result = NULL;
    struct stat st;
    int rc;
    int rows;
    int fetch_rc;
    char got0[64];
    char got1[64];
    unsigned long long affected = 0;

    /* Host for sqlite3 is the directory holding the file (upstream odbxtest
     * passes -h <dir>/ with a trailing slash). */
    if (snprintf(host, sizeof(host), "%s%s", rawdir,
                 rawdir[strlen(rawdir) - 1] == '/' ? "" : "/") >= (int)sizeof(host)) {
        printf("FAIL: db dir too long\n");
        return 1;
    }
    if (snprintf(dbpath, sizeof(dbpath), "%s%s", host, dbfile) >= (int)sizeof(dbpath)) {
        printf("FAIL: db path too long\n");
        return 1;
    }
    remove(dbpath);

    rc = odbx_init(&handle, backend, host, "");
    CHECK(rc == ODBX_ERR_SUCCESS, "upstream-init-sqlite3-backend");
    if (rc != ODBX_ERR_SUCCESS) {
        printf("FAIL: odbx_init(%s) rc=%d err=%s\n", backend, rc,
               odbx_error(NULL, rc));
        printf("test_upstream_sqlite3: %d passed, %d failed\n", passed, failed);
        return 1;
    }

    rc = odbx_bind(handle, dbfile, NULL, NULL, ODBX_BIND_SIMPLE);
    CHECK(rc == ODBX_ERR_SUCCESS, "upstream-bind-sqlite3-file");
    if (rc != ODBX_ERR_SUCCESS) {
        printf("FAIL: odbx_bind rc=%d err=%s\n", rc, odbx_error(handle, rc));
        odbx_finish(handle);
        printf("test_upstream_sqlite3: %d passed, %d failed\n", passed, failed);
        return 1;
    }

    rc = exec_norows(handle, "CREATE TABLE hmbs_t(id INTEGER PRIMARY KEY, val TEXT)", NULL);
    CHECK(rc == 0, "upstream-create-table");

    affected = 0;
    rc = exec_norows(handle, "INSERT INTO hmbs_t(val) VALUES('alpha')", &affected);
    CHECK(rc == 0, "upstream-insert-alpha");
    rc = exec_norows(handle, "INSERT INTO hmbs_t(val) VALUES('beta')", &affected);
    CHECK(rc == 0, "upstream-insert-beta");
    CHECK(affected >= 2, "upstream-rows-affected");

    /* SELECT path: same fetch loop odbxtest uses (result -> row_fetch ->
     * field_value), verifying content, not just the return code. */
    got0[0] = '\0';
    got1[0] = '\0';
    rows = 0;
    rc = odbx_query(handle, "SELECT val FROM hmbs_t ORDER BY id", 0);
    CHECK(rc == ODBX_ERR_SUCCESS, "upstream-select-query");
    if (rc == ODBX_ERR_SUCCESS) {
        int saw_rows = 0;
        for (;;) {
            result = NULL;
            rc = odbx_result(handle, &result, NULL, 0);
            if (rc == ODBX_RES_DONE) {
                break;
            }
            if (rc == ODBX_RES_ROWS) {
                saw_rows = 1;
                while ((fetch_rc = odbx_row_fetch(result)) == ODBX_ROW_NEXT) {
                    const char* v = odbx_field_value(result, 0);
                    if (rows == 0 && v != NULL) {
                        snprintf(got0, sizeof(got0), "%s", v);
                    } else if (rows == 1 && v != NULL) {
                        snprintf(got1, sizeof(got1), "%s", v);
                    }
                    ++rows;
                }
                odbx_result_finish(result);
                result = NULL;
                if (fetch_rc < 0 && fetch_rc != ODBX_ROW_DONE) {
                    printf("FAIL: row_fetch rc=%d\n", fetch_rc);
                    break;
                }
                continue;
            }
            if (rc == ODBX_RES_NOROWS) {
                if (result != NULL) {
                    odbx_result_finish(result);
                    result = NULL;
                }
                continue;
            }
            printf("FAIL: select result rc=%d err=%s\n", rc,
                   odbx_error(handle, rc < 0 ? rc : -ODBX_ERR_BACKEND));
            if (result != NULL) {
                odbx_result_finish(result);
                result = NULL;
            }
            break;
        }
        CHECK(saw_rows, "upstream-select-has-rows");
        CHECK(rows == 2, "upstream-select-row-count");
        CHECK(strcmp(got0, "alpha") == 0, "upstream-select-row-alpha");
        CHECK(strcmp(got1, "beta") == 0, "upstream-select-row-beta");
    }

    rc = exec_norows(handle, "DROP TABLE hmbs_t", NULL);
    CHECK(rc == 0, "upstream-drop-table");

    CHECK(odbx_unbind(handle) == ODBX_ERR_SUCCESS, "upstream-unbind");
    CHECK(odbx_finish(handle) == ODBX_ERR_SUCCESS, "upstream-finish");
    handle = NULL;

    /* Anti-false-pass: the file DB must really exist on disk and be
     * non-empty, proving SQL actually executed (not empty-vs-empty). */
    CHECK(stat(dbpath, &st) == 0, "upstream-dbfile-exists");
    CHECK(st.st_size > 0, "upstream-dbfile-nonempty");
    remove(dbpath);

    printf("test_upstream_sqlite3: %d passed, %d failed\n", passed, failed);
    return failed ? 1 : 0;
}
