#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include "cdb.h"

int main(void) {
    const char *tmpdir = getenv("TMPDIR");
    if (!tmpdir) tmpdir = "/tmp";
    char path[256];
    snprintf(path, sizeof(path), "%s/test_cdb.cdb", tmpdir);

    /* Create a CDB database */
    int fd = open(path, O_RDWR | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) {
        perror("open(create)");
        return 1;
    }

    struct cdb_make cdbm;
    if (cdb_make_start(&cdbm, fd) != 0) {
        perror("cdb_make_start");
        close(fd);
        return 1;
    }

    const char *key = "hello";
    const char *val = "world";
    if (cdb_make_add(&cdbm, key, strlen(key), val, strlen(val)) != 0) {
        fprintf(stderr, "FAIL: cdb_make_add failed for key '%s'\n", key);
        close(fd);
        unlink(path);
        return 1;
    }

    const char *key2 = "foo";
    const char *val2 = "bar";
    if (cdb_make_add(&cdbm, key2, strlen(key2), val2, strlen(val2)) != 0) {
        fprintf(stderr, "FAIL: cdb_make_add failed for key '%s'\n", key2);
        close(fd);
        unlink(path);
        return 1;
    }

    if (cdb_make_finish(&cdbm) != 0) {
        perror("cdb_make_finish");
        close(fd);
        unlink(path);
        return 1;
    }
    close(fd);

    /* Read back and verify */
    fd = open(path, O_RDONLY);
    if (fd < 0) {
        perror("open(read)");
        return 1;
    }

    struct cdb cdb;
    if (cdb_init(&cdb, fd) != 0) {
        perror("cdb_init");
        close(fd);
        return 1;
    }

    /* Query "hello" → "world" */
    if (cdb_find(&cdb, key, strlen(key)) > 0) {
        unsigned vpos = cdb_datapos(&cdb);
        unsigned vlen = cdb_datalen(&cdb);
        char buf[256];
        if (cdb_read(&cdb, buf, vlen, vpos) != 0) {
            perror("cdb_read");
            cdb_free(&cdb);
            close(fd);
            return 1;
        }
        buf[vlen] = '\0';
        if (strcmp(buf, val) != 0) {
            fprintf(stderr, "FAIL: expected '%s', got '%s'\n", val, buf);
            cdb_free(&cdb);
            close(fd);
            return 1;
        }
        printf("OK: %s -> %s\n", key, buf);
    } else {
        fprintf(stderr, "FAIL: key '%s' not found\n", key);
        cdb_free(&cdb);
        close(fd);
        return 1;
    }

    /* Query "foo" → "bar" */
    if (cdb_find(&cdb, key2, strlen(key2)) > 0) {
        unsigned vpos = cdb_datapos(&cdb);
        unsigned vlen = cdb_datalen(&cdb);
        char buf[256];
        if (cdb_read(&cdb, buf, vlen, vpos) != 0) {
            perror("cdb_read");
            cdb_free(&cdb);
            close(fd);
            return 1;
        }
        buf[vlen] = '\0';
        if (strcmp(buf, val2) != 0) {
            fprintf(stderr, "FAIL: expected '%s', got '%s'\n", val2, buf);
            cdb_free(&cdb);
            close(fd);
            return 1;
        }
        printf("OK: %s -> %s\n", key2, buf);
    } else {
        fprintf(stderr, "FAIL: key '%s' not found\n", key2);
        cdb_free(&cdb);
        close(fd);
        return 1;
    }

    /* Query nonexistent key → should not find */
    if (cdb_find(&cdb, "nokey", 5) == 0) {
        printf("OK: 'nokey' correctly not found\n");
    } else {
        fprintf(stderr, "FAIL: 'nokey' should not be found\n");
        cdb_free(&cdb);
        close(fd);
        return 1;
    }

    cdb_free(&cdb);
    close(fd);
    unlink(path);

    printf("All tests passed!\n");
    return 0;
}
