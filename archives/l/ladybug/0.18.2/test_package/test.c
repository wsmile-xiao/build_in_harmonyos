#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>

#include "lbug.h"

/*
 * R34 实质测试：调用被测包 lbug 的 C API（liblbug），创建内存数据库、
 * 建表、写入节点、查询并校验结果。
 *
 * 注意：OHOS 下默认 max_db_size 为 8TB 的 mmap 会因地址空间限制失败
 * （平台限制，见 notes.md），测试显式设置较小的 max_db_size。
 */
int main(void) {
    lbug_database db;
    lbug_connection conn;
    lbug_query_result result;
    lbug_state st;
    int ret = 1;

    lbug_system_config config = lbug_default_system_config();
    config.max_db_size = 268435456; /* 256MB，规避 OHOS 8TB mmap 限制 */

    if (lbug_database_init("", config, &db) != LbugSuccess) {
        printf("FAIL: lbug_database_init\n");
        return 1;
    }
    if (lbug_connection_init(&db, &conn) != LbugSuccess) {
        printf("FAIL: lbug_connection_init\n");
        goto cleanup_db;
    }

    st = lbug_connection_query(
        &conn, "CREATE NODE TABLE Person(name STRING, age INT64, PRIMARY KEY(name));", &result);
    if (st != LbugSuccess || !lbug_query_result_is_success(&result)) {
        printf("FAIL: create node table\n");
        if (st == LbugSuccess) {
            lbug_query_result_destroy(&result); /* 查询已执行但结果失败，销毁避免泄漏 */
        }
        goto cleanup_conn;
    }
    lbug_query_result_destroy(&result);

    st = lbug_connection_query(&conn, "CREATE (:Person {name: 'Alice', age: 25});", &result);
    if (st != LbugSuccess || !lbug_query_result_is_success(&result)) {
        printf("FAIL: create node\n");
        if (st == LbugSuccess) {
            lbug_query_result_destroy(&result); /* 查询已执行但结果失败，销毁避免泄漏 */
        }
        goto cleanup_conn;
    }
    lbug_query_result_destroy(&result);

    st = lbug_connection_query(
        &conn, "MATCH (a:Person) RETURN a.name AS NAME, a.age AS AGE;", &result);
    if (st != LbugSuccess || !lbug_query_result_is_success(&result)) {
        printf("FAIL: match query\n");
        if (st == LbugSuccess) {
            lbug_query_result_destroy(&result); /* 查询已执行但结果失败，销毁避免泄漏 */
        }
        goto cleanup_conn;
    }

    int row_count = 0;
    while (lbug_query_result_has_next(&result)) {
        lbug_flat_tuple tuple;
        lbug_value value;
        lbug_query_result_get_next(&result, &tuple);

        lbug_flat_tuple_get_value(&tuple, 0, &value);
        char* name = NULL;
        lbug_value_get_string(&value, &name);
        lbug_value_destroy(&value); /* 销毁列 0 的 Value（持有字符串） */

        lbug_flat_tuple_get_value(&tuple, 1, &value);
        int64_t age = 0;
        lbug_value_get_int64(&value, &age);
        lbug_value_destroy(&value); /* 销毁列 1 的 Value */

        printf("row: name=%s age=%" PRIi64 "\n", name ? name : "(null)", age);
        if (name && age == 25) {
            row_count++;
        }
        lbug_destroy_string(name);
        lbug_flat_tuple_destroy(&tuple);
    }
    lbug_query_result_destroy(&result);

    if (row_count != 1) {
        printf("FAIL: expected 1 matching row, got %d\n", row_count);
        goto cleanup_conn;
    }

    printf("PASS: lbug C API (create/match roundtrip)\n");
    ret = 0;

cleanup_conn:
    lbug_connection_destroy(&conn);
cleanup_db:
    lbug_database_destroy(&db);
    return ret;
}
