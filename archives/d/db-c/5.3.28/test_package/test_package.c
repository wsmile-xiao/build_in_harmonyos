#include <db.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    const char path[] = "db-c-conan-consumer.db";
    const char key_text[] = "harmony";
    const char value_text[] = "db-c-5.3.28";
    DB *database = NULL;
    DBT key;
    DBT value;
    DBT fetched;
    DBT fetched_value;
    char result[32] = {0};
    int rc;

    remove(path);
    rc = db_create(&database, NULL, 0);
    if (rc != 0) return 1;
    rc = database->open(database, NULL, path, NULL, DB_BTREE, DB_CREATE, 0644);
    if (rc != 0) { database->close(database, 0); return 2; }

    memset(&key, 0, sizeof(key));
    key.data = (void *)key_text;
    key.size = (u_int32_t)sizeof(key_text);
    memset(&value, 0, sizeof(value));
    value.data = (void *)value_text;
    value.size = (u_int32_t)sizeof(value_text);
    if (database->put(database, NULL, &key, &value, 0) != 0) {
        database->close(database, 0);
        remove(path);
        return 3;
    }

    memset(&fetched, 0, sizeof(fetched));
    fetched.data = (void *)key_text;
    fetched.size = (u_int32_t)sizeof(key_text);
    memset(&fetched_value, 0, sizeof(fetched_value));
    fetched_value.data = result;
    fetched_value.ulen = (u_int32_t)sizeof(result);
    fetched_value.flags = DB_DBT_USERMEM;
    rc = database->get(database, NULL, &fetched, &fetched_value, 0);
    if (rc != 0 || fetched_value.size != sizeof(value_text) ||
        memcmp(result, value_text, sizeof(value_text)) != 0) {
        database->close(database, 0);
        remove(path);
        return 4;
    }

    database->close(database, 0);
    remove(path);
    puts("db-c consumer PASS");
    return 0;
}
