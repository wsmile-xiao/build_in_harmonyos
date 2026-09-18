/*
 * tdb 1.4.15 consumer test — exercises the public C API of the packaged library.
 * Real API calls: tdb_open / tdb_store / tdb_fetch / tdb_delete / tdb_close.
 */
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "tdb.h"

static int checks;
static int failures;

#define CHECK(cond, msg)                        \
    do {                                        \
        checks++;                               \
        if (!(cond)) {                          \
            failures++;                         \
            fprintf(stderr, "FAIL: %s\n", msg); \
        }                                       \
    } while (0)

int main(void)
{
    TDB_CONTEXT *tdb;
    TDB_DATA key, value, got;
    int rc;

    unlink("test_tdb.tdb");

    tdb = tdb_open("test_tdb.tdb", 0, TDB_CLEAR_IF_FIRST,
                   O_RDWR | O_CREAT, 0600);
    CHECK(tdb != NULL, "tdb_open creates a database");
    if (tdb == NULL) {
        printf("tdb consumer test: %d checks, %d failures\n", checks, failures);
        return 1;
    }

    key.dptr = (unsigned char *)"greeting";
    key.dsize = strlen((char *)key.dptr);
    value.dptr = (unsigned char *)"hello-ohos";
    value.dsize = strlen((char *)value.dptr);

    rc = tdb_store(tdb, key, value, TDB_REPLACE);
    CHECK(rc == 0, "tdb_store returns 0 for a new key");

    got = tdb_fetch(tdb, key);
    CHECK(got.dptr != NULL, "tdb_fetch returns data for the stored key");
    CHECK(got.dsize == value.dsize, "tdb_fetch returns the stored size");
    CHECK(got.dptr != NULL && got.dsize == value.dsize &&
              memcmp(got.dptr, value.dptr, got.dsize) == 0,
          "tdb_fetch returns the stored content");
    free(got.dptr);

    rc = tdb_delete(tdb, key);
    CHECK(rc == 0, "tdb_delete removes the key");

    got = tdb_fetch(tdb, key);
    CHECK(got.dptr == NULL, "tdb_fetch returns empty after delete");
    free(got.dptr);

    key.dptr = (unsigned char *)"persist";
    key.dsize = strlen((char *)key.dptr);
    value.dptr = (unsigned char *)"kept-for-dump";
    value.dsize = strlen((char *)value.dptr);
    rc = tdb_store(tdb, key, value, TDB_REPLACE);
    CHECK(rc == 0, "tdb_store keeps a second key for tdbdump");

    rc = tdb_close(tdb);
    CHECK(rc == 0, "tdb_close");

    printf("tdb consumer test: %d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
