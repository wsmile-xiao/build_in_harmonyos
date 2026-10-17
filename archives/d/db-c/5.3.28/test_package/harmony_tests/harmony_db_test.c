#include <db.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    DB *database = NULL;
    DBT key;
    DBT value;
    const char path[] = "db-c-harmony-test.db";
    const char key_text[] = "ohos";
    const char value_text[] = "db-c";
    int rc = db_create(&database, NULL, 0);
    if (rc != 0) return 1;
    rc = database->open(database, NULL, path, NULL, DB_BTREE,
                        DB_CREATE | DB_TRUNCATE, 0600);
    if (rc != 0) {
        database->close(database, 0);
        return 2;
    }
    memset(&key, 0, sizeof(key));
    key.data = (void *)key_text;
    key.size = (u_int32_t)sizeof(key_text);
    memset(&value, 0, sizeof(value));
    value.data = (void *)value_text;
    value.size = (u_int32_t)sizeof(value_text);
    rc = database->put(database, NULL, &key, &value, 0);
    database->close(database, 0);
    remove(path);
    if (rc != 0) return 3;
    puts("HARMONY_TEST_PASS=1/1");
    return 0;
}
