#include <db.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    DB *dbp;
    DBT key, data;
    int ret;

    /* Create a database handle */
    ret = db_create(&dbp, NULL, 0);
    if (ret != 0) {
        fprintf(stderr, "db_create failed: %s\n", db_strerror(ret));
        return 1;
    }

    /* Open the database in memory (DB_BTREE, create if not exists) */
    ret = dbp->open(dbp, NULL, "test.db", NULL, DB_BTREE, DB_CREATE, 0600);
    if (ret != 0) {
        fprintf(stderr, "dbp->open failed: %s\n", db_strerror(ret));
        dbp->close(dbp, 0);
        return 1;
    }

    /* Put a key-value pair */
    memset(&key, 0, sizeof(key));
    memset(&data, 0, sizeof(data));
    key.data = "hello";
    key.size = strlen("hello") + 1;
    data.data = "world";
    data.size = strlen("world") + 1;

    ret = dbp->put(dbp, NULL, &key, &data, 0);
    if (ret != 0) {
        fprintf(stderr, "dbp->put failed: %s\n", db_strerror(ret));
        dbp->close(dbp, 0);
        remove("test.db");
        return 1;
    }

    /* Get the value back */
    memset(&key, 0, sizeof(key));
    memset(&data, 0, sizeof(data));
    key.data = "hello";
    key.size = strlen("hello") + 1;

    ret = dbp->get(dbp, NULL, &key, &data, 0);
    if (ret != 0) {
        fprintf(stderr, "dbp->get failed: %s\n", db_strerror(ret));
        dbp->close(dbp, 0);
        remove("test.db");
        return 1;
    }

    /* Verify the value */
    if (strcmp((char *)data.data, "world") == 0) {
        printf("Berkeley DB test passed: hello=world\n");
    } else {
        fprintf(stderr, "Value mismatch: got '%s' expected 'world'\n", (char *)data.data);
        dbp->close(dbp, 0);
        remove("test.db");
        return 1;
    }

    /* Close the database */
    ret = dbp->close(dbp, 0);
    if (ret != 0) {
        fprintf(stderr, "dbp->close failed: %s\n", db_strerror(ret));
        return 1;
    }

    /* Clean up */
    remove("test.db");

    return 0;
}
