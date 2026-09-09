#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include "cdb.h"
#include "cdb_make.h"

/* Round-trip test against the 32-bit cdb API: build a database with
 * cdb_make_*(), then query it back with cdb_find()/cdb_read(). */

int main(void) {
    const char *tmpdir = getenv("TMPDIR");
    if (!tmpdir) tmpdir = "/tmp";
    char path[512];
    snprintf(path, sizeof(path), "%s/test_cdb.cdb", tmpdir);

    const char *k1 = "hello", *v1 = "world";
    const char *k2 = "foo",   *v2 = "bar";

    int fd = open(path, O_RDWR | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) { perror("open(create)"); return 1; }

    struct cdb_make cdbm;
    if (cdb_make_start(&cdbm, fd) != 0) {
        fprintf(stderr, "FAIL: cdb_make_start\n");
        close(fd);
        return 1;
    }
    if (cdb_make_add(&cdbm, k1, strlen(k1), v1, strlen(v1)) != 0) {
        fprintf(stderr, "FAIL: cdb_make_add '%s'\n", k1);
        return 1;
    }
    if (cdb_make_add(&cdbm, k2, strlen(k2), v2, strlen(v2)) != 0) {
        fprintf(stderr, "FAIL: cdb_make_add '%s'\n", k2);
        return 1;
    }
    if (cdb_make_finish(&cdbm) != 0) {
        fprintf(stderr, "FAIL: cdb_make_finish\n");
        return 1;
    }
    close(fd);

    fd = open(path, O_RDONLY);
    if (fd < 0) { perror("open(read)"); return 1; }

    struct cdb cdb;
    cdb_init(&cdb, fd);

    /* query k1 -> v1 */
    if (cdb_find(&cdb, k1, strlen(k1)) != 1) {
        fprintf(stderr, "FAIL: key '%s' not found\n", k1);
        return 1;
    }
    char buf[256];
    num vpos = cdb_datapos(&cdb), vlen = cdb_datalen(&cdb);
    if (vlen != (num)strlen(v1)) {
        fprintf(stderr, "FAIL: '%s' len %lld != %zu\n", k1, (long long)vlen, strlen(v1));
        return 1;
    }
    if (cdb_read(&cdb, buf, vlen, vpos) != 0) {
        fprintf(stderr, "FAIL: cdb_read '%s'\n", k1);
        return 1;
    }
    buf[vlen] = '\0';
    if (strcmp(buf, v1) != 0) {
        fprintf(stderr, "FAIL: '%s' -> '%s' (want '%s')\n", k1, buf, v1);
        return 1;
    }
    printf("OK: %s -> %s\n", k1, buf);

    /* query k2 -> v2 */
    if (cdb_find(&cdb, k2, strlen(k2)) != 1) {
        fprintf(stderr, "FAIL: key '%s' not found\n", k2);
        return 1;
    }
    vpos = cdb_datapos(&cdb); vlen = cdb_datalen(&cdb);
    if (cdb_read(&cdb, buf, vlen, vpos) != 0 || vlen != (num)strlen(v2)) {
        fprintf(stderr, "FAIL: cdb_read '%s'\n", k2);
        return 1;
    }
    buf[vlen] = '\0';
    if (strcmp(buf, v2) != 0) {
        fprintf(stderr, "FAIL: '%s' -> '%s' (want '%s')\n", k2, buf, v2);
        return 1;
    }
    printf("OK: %s -> %s\n", k2, buf);

    /* miss must return 0 */
    if (cdb_find(&cdb, "nokey", 5) == 0) {
        printf("OK: 'nokey' correctly not found\n");
    } else {
        fprintf(stderr, "FAIL: 'nokey' should not be found\n");
        return 1;
    }

    /* exercise the exported hash function */
    num h = cdb_hash("hello", 5);
    printf("OK: cdb_hash(hello) = %lld\n", (long long)h);

    cdb_free(&cdb);
    close(fd);
    unlink(path);

    printf("All cdb tests passed!\n");
    return 0;
}
