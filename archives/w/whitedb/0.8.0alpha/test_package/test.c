#include <stdio.h>
#include <whitedb/dbapi.h>

/* test_whitedb: 消费者视角验证 whitedb 核心读写功能
 * 使用上游公开 API: wg_attach_local_database / wg_create_record /
 * wg_encode_int / wg_encode_str / wg_set_field / wg_get_field /
 * wg_decode_int / wg_decode_str / wg_delete_local_database
 */
int main(void) {
    void *db = wg_attach_local_database(1000000);
    if (!db) {
        printf("FAIL: wg_attach_local_database returned NULL\n");
        return 1;
    }

    void *rec = wg_create_record(db, 2);
    if (!rec) {
        printf("FAIL: wg_create_record returned NULL\n");
        wg_delete_local_database(db);
        return 1;
    }

    /* 写入 int 字段并读回验证 */
    wg_set_field(db, rec, 0, wg_encode_int(db, 42));
    wg_int v = wg_get_field(db, rec, 0);
    if (wg_decode_int(db, v) != 42) {
        printf("FAIL: int field roundtrip mismatch (%lld)\n", (long long)wg_decode_int(db, v));
        wg_delete_local_database(db);
        return 1;
    }

    /* 写入 str 字段并读回验证 */
    wg_set_field(db, rec, 1, wg_encode_str(db, "whitedb", NULL));
    char *s = wg_decode_str(db, wg_get_field(db, rec, 1));
    if (!s || s[0] != 'w') {
        printf("FAIL: str field roundtrip mismatch\n");
        wg_delete_local_database(db);
        return 1;
    }

    wg_delete_local_database(db);
    printf("PASS: whitedb int/str field roundtrip OK\n");
    return 0;
}
