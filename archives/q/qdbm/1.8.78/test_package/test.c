#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <depot.h>

int main(void) {
    const char *dbname = "test_qdbm.db";
    DEPOT *depot;
    char *val;
    int vsize;

    /* Open a database for writing (create if not exists) */
    depot = dpopen(dbname, DP_OWRITER | DP_OCREAT, -1);
    if (!depot) {
        fprintf(stderr, "dpopen failed\n");
        return 1;
    }

    /* Store a key-value pair */
    if (!dpput(depot, "key1", 4, "value1", 6, DP_DOVER)) {
        fprintf(stderr, "dpput failed\n");
        dpclose(depot);
        return 1;
    }

    /* Retrieve the value */
    val = dpget(depot, "key1", 4, 0, -1, &vsize);
    if (!val) {
        fprintf(stderr, "dpget failed\n");
        dpclose(depot);
        return 1;
    }

    if (vsize == 6 && memcmp(val, "value1", 6) == 0) {
        printf("qdbm test: OK (put/get verified)\n");
    } else {
        fprintf(stderr, "qdbm test: FAIL (value mismatch)\n");
        free(val);
        dpclose(depot);
        return 1;
    }
    free(val);

    /* Delete the key */
    if (!dpout(depot, "key1", 4)) {
        fprintf(stderr, "dpout failed\n");
        dpclose(depot);
        return 1;
    }

    /* Verify deletion */
    val = dpget(depot, "key1", 4, 0, -1, &vsize);
    if (val != NULL) {
        fprintf(stderr, "qdbm test: FAIL (key should be deleted)\n");
        free(val);
        dpclose(depot);
        return 1;
    }

    /* Close the database */
    if (!dpclose(depot)) {
        fprintf(stderr, "dpclose failed\n");
        remove(dbname);
        return 1;
    }

    /* Clean up */
    if (remove(dbname) != 0) {
        fprintf(stderr, "warning: failed to remove %s\n", dbname);
    }

    printf("qdbm test: ALL PASSED\n");
    return 0;
}
