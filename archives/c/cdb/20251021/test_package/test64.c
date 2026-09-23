#define CDB64 1
#include "cdb.h"
#include "cdb_make.h"

/* Same round-trip as test.c, but with CDB64 defined: the cdb_* names are
 * macro-renamed to cdb64_* (64-bit hash and offsets), linking against the
 * cdb64 objects inside libcdb.a. */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>

int main(void) {
    const char *tmpdir = getenv("TMPDIR");
    if (!tmpdir) tmpdir = "/tmp";
    char path[512];
    snprintf(path, sizeof(path), "%s/test_cdb64.cdb64", tmpdir);

    const char *k1 = "alpha", *v1 = "one";
    const char *k2 = "beta",  *v2 = "two";

    int fd = open(path, O_RDWR | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) { perror("open(create)"); return 1; }

    struct cdb_make cdbm; /* becomes struct cdb64_make via CDB64 renaming */
    if (cdb_make_start(&cdbm, fd) != 0) {
        fprintf(stderr, "FAIL: cdb64_make_start\n");
        close(fd);
        return 1;
    }
    if (cdb_make_add(&cdbm, k1, strlen(k1), v1, strlen(v1)) != 0) {
        fprintf(stderr, "FAIL: cdb64_make_add '%s'\n", k1);
        return 1;
    }
    if (cdb_make_add(&cdbm, k2, strlen(k2), v2, strlen(v2)) != 0) {
        fprintf(stderr, "FAIL: cdb64_make_add '%s'\n", k2);
        return 1;
    }
    if (cdb_make_finish(&cdbm) != 0) {
        fprintf(stderr, "FAIL: cdb64_make_finish\n");
        return 1;
    }
    close(fd);

    fd = open(path, O_RDONLY);
    if (fd < 0) { perror("open(read)"); return 1; }

    struct cdb cdb; /* becomes struct cdb64 via CDB64 renaming */
    cdb_init(&cdb, fd);

    if (cdb_find(&cdb, k1, strlen(k1)) != 1) {
        fprintf(stderr, "FAIL: key '%s' not found\n", k1);
        return 1;
    }
    char buf[256];
    num vpos = cdb_datapos(&cdb), vlen = cdb_datalen(&cdb);
    if (cdb_read(&cdb, buf, vlen, vpos) != 0) {
        fprintf(stderr, "FAIL: cdb64_read '%s'\n", k1);
        return 1;
    }
    buf[vlen] = '\0';
    if (strcmp(buf, v1) != 0) {
        fprintf(stderr, "FAIL: '%s' -> '%s' (want '%s')\n", k1, buf, v1);
        return 1;
    }
    printf("OK cdb64: %s -> %s\n", k1, buf);

    if (cdb_find(&cdb, k2, strlen(k2)) != 1) {
        fprintf(stderr, "FAIL: key '%s' not found\n", k2);
        return 1;
    }
    vpos = cdb_datapos(&cdb); vlen = cdb_datalen(&cdb);
    if (cdb_read(&cdb, buf, vlen, vpos) != 0) {
        fprintf(stderr, "FAIL: cdb64_read '%s'\n", k2);
        return 1;
    }
    buf[vlen] = '\0';
    if (strcmp(buf, v2) != 0) {
        fprintf(stderr, "FAIL: '%s' -> '%s' (want '%s')\n", k2, buf, v2);
        return 1;
    }
    printf("OK cdb64: %s -> %s\n", k2, buf);

    if (cdb_find(&cdb, "nokey", 5) == 0) {
        printf("OK cdb64: 'nokey' correctly not found\n");
    } else {
        fprintf(stderr, "FAIL: 'nokey' should not be found\n");
        return 1;
    }

    cdb_free(&cdb);
    close(fd);
    unlink(path);

    printf("All cdb64 tests passed!\n");
    return 0;
}
