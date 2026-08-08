#include <stdio.h>
#include <stdlib.h>
#include <db.h>

int main(void) {
    DB *dbp = NULL;
    int ret;

    /* Create a database handle and verify the DB API is usable */
    ret = db_create(&dbp, NULL, 0);
    if (ret != 0) {
        fprintf(stderr, "db_create failed: %d\n", ret);
        return 1;
    }
    printf("db_create OK\n");

    ret = dbp->close(dbp, 0);
    if (ret != 0) {
        fprintf(stderr, "db->close failed: %d\n", ret);
        return 1;
    }
    printf("berkeley-db5 5.3.28: API test PASSED\n");
    return 0;
}
