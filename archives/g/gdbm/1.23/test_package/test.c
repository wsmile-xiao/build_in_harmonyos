#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <gdbm.h>

int main(void) {
    GDBM_FILE dbf;
    datum key, value, result;
    int rc;

    /* Open/create database in current directory */
    dbf = gdbm_open("test_gdbm.db", 0, GDBM_WRCREAT, 0644, NULL);
    if (!dbf) {
        fprintf(stderr, "gdbm_open failed: %s\n", gdbm_strerror(gdbm_errno));
        return 1;
    }

    /* Store a key-value pair */
    key.dptr = "hello";
    key.dsize = strlen(key.dptr);
    value.dptr = "world";
    value.dsize = strlen(value.dptr);
    rc = gdbm_store(dbf, key, value, GDBM_REPLACE);
    if (rc != 0) {
        fprintf(stderr, "gdbm_store failed\n");
        gdbm_close(dbf);
        return 1;
    }

    /* Fetch the value by key */
    result = gdbm_fetch(dbf, key);
    if (result.dptr == NULL) {
        fprintf(stderr, "gdbm_fetch failed\n");
        gdbm_close(dbf);
        return 1;
    }

    /* Verify the value content */
    if (result.dsize != 5 || memcmp(result.dptr, "world", 5) != 0) {
        fprintf(stderr, "value mismatch: got %.*s\n", result.dsize, result.dptr);
        free(result.dptr);
        gdbm_close(dbf);
        return 1;
    }

    free(result.dptr);
    gdbm_close(dbf);

    printf("gdbm test passed!\n");
    return 0;
}
