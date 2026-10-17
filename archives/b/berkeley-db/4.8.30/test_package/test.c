#include <stdio.h>

#include "db.h"

int main(void)
{
    DB *dbp;
    int ret = db_create(&dbp, NULL, 0);
    if (ret != 0) {
        fprintf(stderr, "db_create failed: %d\n", ret);
        return 1;
    }

    ret = dbp->open(dbp, NULL, "test.db", NULL, DB_BTREE, DB_CREATE, 0600);
    if (ret != 0) {
        fprintf(stderr, "db_open failed: %d\n", ret);
        dbp->close(dbp, 0);
        return 1;
    }

    dbp->close(dbp, 0);
    puts("Berkeley DB test passed!");
    return 0;
}
