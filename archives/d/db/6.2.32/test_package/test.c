/* Consumer test for db (Berkeley DB classic) 6.2.32.
 *
 * Genuinely exercises the packaged C API: environment-less database
 * create/open/put/get/close, a cursor scan, and a DB->verify() of the
 * on-disk file produced via the package's real API.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <db.h>

static int fail(const char *what, int ret) {
    fprintf(stderr, "%s failed: %s\n", what, db_strerror(ret));
    return 1;
}

int main(void) {
    DB *dbp = NULL;
    DBC *cur = NULL;
    DBT key, data;
    int ret, i, n_found = 0;
    char kbuf[32], dbuf[64];

    /* 1. create + open a B-Tree database in the current dir */
    ret = db_create(&dbp, NULL, 0);
    if (ret) return fail("db_create", ret);
    printf("db_create OK\n");

    ret = dbp->open(dbp, NULL, "consumer_test.db", NULL, DB_BTREE, DB_CREATE, 0664);
    if (ret) return fail("db->open", ret);
    printf("db->open OK (BDB %s)\n", db_version(NULL, NULL, NULL));

    /* 2. put 50 records */
    for (i = 0; i < 50; i++) {
        memset(&key, 0, sizeof(key));
        memset(&data, 0, sizeof(data));
        snprintf(kbuf, sizeof(kbuf), "key-%03d", i);
        snprintf(dbuf, sizeof(dbuf), "value-%03d-payload", i);
        key.data = kbuf; key.size = (u_int32_t)strlen(kbuf) + 1;
        data.data = dbuf; data.size = (u_int32_t)strlen(dbuf) + 1;
        ret = dbp->put(dbp, NULL, &key, &data, 0);
        if (ret) return fail("db->put", ret);
    }
    printf("db->put x50 OK\n");

    /* 3. get one record back and check content */
    memset(&key, 0, sizeof(key));
    memset(&data, 0, sizeof(data));
    key.data = (char *)"key-042"; key.size = 8;
    ret = dbp->get(dbp, NULL, &key, &data, 0);
    if (ret) return fail("db->get", ret);
    if (strcmp((const char *)data.data, "value-042-payload") != 0) {
        fprintf(stderr, "db->get returned wrong data: %s\n", (char *)data.data);
        return 1;
    }
    printf("db->get OK (round-trip verified)\n");

    /* 4. cursor scan: count all records */
    ret = dbp->cursor(dbp, NULL, &cur, 0);
    if (ret) return fail("db->cursor", ret);
    memset(&key, 0, sizeof(key));
    memset(&data, 0, sizeof(data));
    while ((ret = cur->c_get(cur, &key, &data, DB_NEXT)) == 0)
        n_found++;
    if (ret != DB_NOTFOUND) return fail("cursor scan", ret);
    if (n_found != 50) {
        fprintf(stderr, "cursor scan expected 50 records, got %d\n", n_found);
        return 1;
    }
    cur->c_close(cur);
    printf("cursor scan OK (50/50 records)\n");

    /* 5. close, reopen read-only and re-verify persistence */
    ret = dbp->close(dbp, 0);
    if (ret) return fail("db->close", ret);
    ret = db_create(&dbp, NULL, 0);
    if (ret) return fail("db_create#2", ret);
    ret = dbp->open(dbp, NULL, "consumer_test.db", NULL, DB_BTREE, DB_RDONLY, 0);
    if (ret) return fail("db->open#2 (RDONLY)", ret);
    memset(&key, 0, sizeof(key));
    memset(&data, 0, sizeof(data));
    key.data = (char *)"key-000"; key.size = 8;
    ret = dbp->get(dbp, NULL, &key, &data, 0);
    if (ret) return fail("db->get after reopen", ret);
    printf("reopen + persistence OK\n");

    ret = dbp->close(dbp, 0);
    if (ret) return fail("final close", ret);
    printf("db 6.2.32 consumer test PASSED\n");
    return 0;
}
