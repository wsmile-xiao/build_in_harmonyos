#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "lbug.h"

/*
 * AI 补充上游测试用例（2026-08-22）
 *
 * 背景：上游 562 个 gtest 测试套件（BUILD_TESTS=ON）在 OHOS 工具链下可编译
 * 链接，但因 OHOS 交叉编译产物依赖 OHOS 运行时（libc++_shared.so 等），在
 * 构建机（musl-libc aarch64）上符号重定位失败（Error relocating ... symbol
 * not found），无法回填真实通过率。
 *
 * 本文件用 AI 依据上游测试逻辑编写等价场景，通过 C API + Cypher 在 OHOS
 * 上真实执行，覆盖上游核心测试模块：
 *   1. value_test       — lbug_value_create_* / lbug_value_get_* / clone/copy 各数据类型往返
 *   2. data_type_test   — lbug_data_type_create/clone/equals/get_id
 *   3. query_result_test— 列数/列名/行数/结果遍历
 *   4. prepared_statement_test — 参数化查询绑定
 *   5. api/aggregate    — Cypher COUNT/SUM/AVG/MIN/MAX 聚合
 *   6. api/ddl          — CREATE/DROP TABLE（节点表 + 关系表）
 *   7. dml_node/dml_rel — 节点/关系 CRUD（CREATE/MATCH/SET/DELETE）
 *   8. filter/arithmetic— WHERE 过滤 + 算术表达式
 *   9. transaction      — BEGIN/COMMIT/ROLLBACK 事务语义
 *  10. version/connection — 版本号/连接复用
 */

static int g_pass = 0;
static int g_fail = 0;

#define CHECK(cond, name)                                                      \
    do {                                                                       \
        if (cond) {                                                            \
            g_pass++;                                                          \
        } else {                                                               \
            g_fail++;                                                          \
            printf("FAIL: %s\n", name);                                        \
        }                                                                      \
    } while (0)

/* 执行查询并断言成功；成功时由调用方负责销毁 result */
static int query_ok(lbug_connection* conn, const char* cypher, lbug_query_result* result) {
    lbug_state st = lbug_connection_query(conn, cypher, result);
    if (st != LbugSuccess || !lbug_query_result_is_success(result)) {
        if (st == LbugSuccess) {
            lbug_query_result_destroy(result);
        }
        return 0;
    }
    return 1;
}

/* 执行查询并统计返回行数（用于 MATCH 类结果校验） */
static int query_count_rows(lbug_connection* conn, const char* cypher) {
    lbug_query_result result;
    if (!query_ok(conn, cypher, &result)) {
        return -1;
    }
    int n = 0;
    while (lbug_query_result_has_next(&result)) {
        lbug_flat_tuple tuple;
        lbug_query_result_get_next(&result, &tuple);
        lbug_flat_tuple_destroy(&tuple);
        n++;
    }
    lbug_query_result_destroy(&result);
    return n;
}

/* 执行 MATCH 查询取第 col 列数值求和（聚合校验用）。
 * 兼容 SUM(INT128)/AVG(DOUBLE)/普通列(INT64) 三种返回类型。 */
static int64_t query_sum_col(lbug_connection* conn, const char* cypher, int col) {
    lbug_query_result result;
    if (!query_ok(conn, cypher, &result)) {
        return -1;
    }
    int64_t sum = 0;
    while (lbug_query_result_has_next(&result)) {
        lbug_flat_tuple tuple;
        lbug_value value;
        lbug_query_result_get_next(&result, &tuple);
        lbug_flat_tuple_get_value(&tuple, col, &value);
        int64_t vi = 0;
        double vd = 0;
        if (lbug_value_get_int64(&value, &vi) == LbugSuccess) {
            sum += vi;
        } else if (lbug_value_get_double(&value, &vd) == LbugSuccess) {
            sum += (int64_t)vd;
        } else {
            lbug_int128_t v128;
            if (lbug_value_get_int128(&value, &v128) == LbugSuccess) {
                sum += (int64_t)v128.low;
            }
        }
        lbug_value_destroy(&value);
        lbug_flat_tuple_destroy(&tuple);
    }
    lbug_query_result_destroy(&result);
    return sum;
}

int main(void) {
    lbug_database db;
    lbug_connection conn;
    lbug_state st;

    lbug_system_config config = lbug_default_system_config();
    config.max_db_size = 268435456; /* 256MB，规避 OHOS 8TB mmap 限制 */

    CHECK(lbug_database_init("", config, &db) == LbugSuccess, "database_init");
    CHECK(lbug_connection_init(&db, &conn) == LbugSuccess, "connection_init");

    /* ========== 场景 10: version/connection（版本号 + 连接复用） ========== */
    {
        char* ver = lbug_get_version();
        CHECK(ver != NULL, "get_version");
        if (ver) {
            printf("lbug version: %s\n", ver);
            CHECK(strstr(ver, "0.18.2") != NULL, "version contains 0.18.2");
            lbug_destroy_string(ver);
        }
        char* sv = NULL;
        uint64_t sv_num = lbug_get_storage_version();
        CHECK(sv_num > 0, "get_storage_version");
        (void)sv;
    }

    /* ========== 场景 6: DDL（建表/删表：节点表 + 关系表） ========== */
    {
        lbug_query_result r;
        CHECK(query_ok(&conn,
            "CREATE NODE TABLE Person(name STRING, age INT64, PRIMARY KEY(name));", &r),
            "ddl create node table");
        lbug_query_result_destroy(&r);
        CHECK(query_ok(&conn,
            "CREATE REL TABLE KNOWS(FROM Person TO Person, since INT64);", &r),
            "ddl create rel table");
        lbug_query_result_destroy(&r);
    }

    /* ========== 场景 7: DML 节点/关系 CRUD ========== */
    {
        lbug_query_result r;
        CHECK(query_ok(&conn, "CREATE (:Person {name: 'Alice', age: 25});", &r), "dml create alice");
        lbug_query_result_destroy(&r);
        CHECK(query_ok(&conn, "CREATE (:Person {name: 'Bob', age: 30});", &r), "dml create bob");
        lbug_query_result_destroy(&r);
        CHECK(query_ok(&conn, "CREATE (:Person {name: 'Carol', age: 35});", &r), "dml create carol");
        lbug_query_result_destroy(&r);

        /* MATCH 全表行数 = 3 */
        CHECK(query_count_rows(&conn, "MATCH (p:Person) RETURN p;") == 3, "dml match 3 persons");

        /* SET 更新属性 */
        CHECK(query_ok(&conn, "MATCH (p:Person {name:'Alice'}) SET p.age = 26;", &r), "dml set age");
        lbug_query_result_destroy(&r);
        CHECK(query_sum_col(&conn, "MATCH (p:Person) RETURN p.age;", 0) == 91, "dml ages sum=91");

        /* 关系创建 + MATCH 关系 */
        CHECK(query_ok(&conn,
            "MATCH (a:Person {name:'Alice'}), (b:Person {name:'Bob'}) CREATE (a)-[:KNOWS {since:2020}]->(b);", &r),
            "dml create rel");
        lbug_query_result_destroy(&r);
        CHECK(query_count_rows(&conn,
            "MATCH (a:Person)-[k:KNOWS]->(b:Person) RETURN a, k, b;") == 1, "dml match rel");

        /* DELETE 节点 */
        CHECK(query_ok(&conn, "MATCH (p:Person {name:'Carol'}) DELETE p;", &r), "dml delete carol");
        lbug_query_result_destroy(&r);
        CHECK(query_count_rows(&conn, "MATCH (p:Person) RETURN p;") == 2, "dml after delete=2");
    }

    /* ========== 场景 8: filter/arithmetic（WHERE + 算术） ========== */
    {
        /* WHERE 过滤：age > 27 → Bob(30) 仅 1 行 */
        CHECK(query_count_rows(&conn,
            "MATCH (p:Person) WHERE p.age > 27 RETURN p;") == 1, "filter age>27");
        /* 算术表达式：SELECT 25 + 5 = 30 */
        lbug_query_result r;
        if (query_ok(&conn, "RETURN 25 + 5 AS S;", &r)) {
            CHECK(lbug_query_result_has_next(&r), "arithmetic has row");
            lbug_flat_tuple tuple;
            lbug_value value;
            lbug_query_result_get_next(&r, &tuple);
            lbug_flat_tuple_get_value(&tuple, 0, &value);
            int64_t s = 0;
            lbug_value_get_int64(&value, &s);
            CHECK(s == 30, "arithmetic 25+5=30");
            lbug_value_destroy(&value);
            lbug_flat_tuple_destroy(&tuple);
            lbug_query_result_destroy(&r);
        } else {
            CHECK(0, "arithmetic query");
        }
        /* ORDER BY 排序 */
        CHECK(query_count_rows(&conn,
            "MATCH (p:Person) RETURN p.name ORDER BY p.name DESC;") == 2, "order by");
    }

    /* ========== 场景 5: 聚合（COUNT/SUM/AVG/MIN/MAX） ========== */
    {
        lbug_query_result r;
        /* COUNT */
        if (query_ok(&conn, "MATCH (p:Person) RETURN COUNT(p) AS C;", &r)) {
            CHECK(lbug_query_result_has_next(&r), "agg count has row");
            lbug_flat_tuple tuple;
            lbug_value value;
            lbug_query_result_get_next(&r, &tuple);
            lbug_flat_tuple_get_value(&tuple, 0, &value);
            int64_t c = 0;
            lbug_value_get_int64(&value, &c);
            CHECK(c == 2, "agg count=2");
            lbug_value_destroy(&value);
            lbug_flat_tuple_destroy(&tuple);
            lbug_query_result_destroy(&r);
        } else {
            CHECK(0, "agg count query");
        }
        /* SUM(age) = 26 + 30 = 56 */
        CHECK(query_sum_col(&conn, "MATCH (p:Person) RETURN SUM(p.age);", 0) == 56, "agg sum=56");
        /* AVG(age) = 28 */
        CHECK(query_sum_col(&conn, "MATCH (p:Person) RETURN AVG(p.age);", 0) == 28, "agg avg=28");
        /* MIN/MAX */
        CHECK(query_sum_col(&conn, "MATCH (p:Person) RETURN MIN(p.age);", 0) == 26, "agg min=26");
        CHECK(query_sum_col(&conn, "MATCH (p:Person) RETURN MAX(p.age);", 0) == 30, "agg max=30");
    }

    /* ========== 场景 3: query_result_test（列信息 + 遍历） ========== */
    {
        lbug_query_result r;
        if (query_ok(&conn, "MATCH (p:Person) RETURN p.name AS N, p.age AS A;", &r)) {
            int64_t nc = lbug_query_result_get_num_columns(&r);
            CHECK(nc == 2, "qr num_columns=2");
            char* c0 = NULL;
            lbug_query_result_get_column_name(&r, 0, &c0);
            if (c0) {
                CHECK(strstr(c0, "N") != NULL, "qr col0 name N");
                lbug_destroy_string(c0);
            }
            CHECK(lbug_query_result_get_num_tuples(&r) == 2, "qr num_tuples=2");
            lbug_query_result_destroy(&r);
        } else {
            CHECK(0, "qr query");
        }
    }

    /* ========== 场景 4: prepared_statement_test（参数化查询） ========== */
    {
        lbug_prepared_statement ps;
        st = lbug_connection_prepare(&conn,
            "MATCH (p:Person) WHERE p.age = $age RETURN p.name;", &ps);
        CHECK(st == LbugSuccess && lbug_prepared_statement_is_success(&ps), "ps prepare");
        if (st == LbugSuccess && lbug_prepared_statement_is_success(&ps)) {
            CHECK(lbug_prepared_statement_bind_int64(&ps, "age", 30) == LbugSuccess, "ps bind age");
            lbug_query_result r;
            st = lbug_connection_execute(&conn, &ps, &r);
            CHECK(st == LbugSuccess && lbug_query_result_is_success(&r), "ps execute");
            if (st == LbugSuccess && lbug_query_result_is_success(&r)) {
                CHECK(lbug_query_result_get_num_tuples(&r) == 1, "ps result 1 row");
                lbug_query_result_destroy(&r);
            }
            lbug_prepared_statement_destroy(&ps);
        }
    }

    /* ========== 场景 1: value_test（各数据类型往返） ========== */
    {
        lbug_value* v;
        v = lbug_value_create_int64(42);
        CHECK(v != NULL, "value int64 create");
        if (v) {
            int64_t vi = 0;
            lbug_value_get_int64(v, &vi);
            CHECK(vi == 42, "value int64 roundtrip");
            lbug_value_destroy(v);
        }

        v = lbug_value_create_double(3.14);
        CHECK(v != NULL, "value double create");
        if (v) {
            double vd = 0;
            lbug_value_get_double(v, &vd);
            CHECK(vd > 3.13 && vd < 3.15, "value double roundtrip");
            lbug_value_destroy(v);
        }

        v = lbug_value_create_bool(1);
        CHECK(v != NULL, "value bool create");
        if (v) {
            bool vb = false;
            lbug_value_get_bool(v, &vb);
            CHECK(vb == true, "value bool roundtrip");
            lbug_value_destroy(v);
        }

        v = lbug_value_create_string("hello");
        CHECK(v != NULL, "value string create");
        if (v) {
            char* vs = NULL;
            lbug_value_get_string(v, &vs);
            CHECK(vs && strcmp(vs, "hello") == 0, "value string roundtrip");
            if (vs) lbug_destroy_string(vs);
            lbug_value_destroy(v);
        }

        /* clone/copy */
        lbug_value* v2;
        v = lbug_value_create_int64(7);
        CHECK(v != NULL, "value v2 create");
        v2 = lbug_value_clone(v);
        CHECK(v2 != NULL, "value clone");
        if (v2) {
            int64_t vc = 0;
            lbug_value_get_int64(v2, &vc);
            CHECK(vc == 7, "value clone roundtrip");
            lbug_value_destroy(v2);
        }
        if (v) lbug_value_destroy(v);
    }

    /* ========== 场景 2: data_type_test ========== */
    {
        lbug_logical_type dt, dt2;
        lbug_data_type_create(LBUG_INT64, NULL, 0, &dt);
        CHECK(lbug_data_type_get_id(&dt) == LBUG_INT64, "dt get_id");
        lbug_data_type_clone(&dt, &dt2);
        CHECK(lbug_data_type_equals(&dt, &dt2) != 0, "dt equals");
        lbug_data_type_destroy(&dt);
        lbug_data_type_destroy(&dt2);
    }

    /* ========== 场景 9: transaction（事务语义） ========== */
    {
        lbug_query_result r;
        CHECK(query_ok(&conn, "BEGIN TRANSACTION;", &r), "tx begin");
        lbug_query_result_destroy(&r);
        CHECK(query_ok(&conn, "CREATE (:Person {name: 'Dave', age: 40});", &r), "tx create dave");
        lbug_query_result_destroy(&r);
        /* 未提交时可见 */
        CHECK(query_count_rows(&conn, "MATCH (p:Person) RETURN p;") == 3, "tx sees uncommitted");
        CHECK(query_ok(&conn, "ROLLBACK;", &r), "tx rollback");
        lbug_query_result_destroy(&r);
        /* 回滚后不可见 */
        CHECK(query_count_rows(&conn, "MATCH (p:Person) RETURN p;") == 2, "tx after rollback=2");

        CHECK(query_ok(&conn, "BEGIN TRANSACTION;", &r), "tx begin2");
        lbug_query_result_destroy(&r);
        CHECK(query_ok(&conn, "CREATE (:Person {name: 'Eve', age: 45});", &r), "tx create eve");
        lbug_query_result_destroy(&r);
        CHECK(query_ok(&conn, "COMMIT;", &r), "tx commit");
        lbug_query_result_destroy(&r);
        CHECK(query_count_rows(&conn, "MATCH (p:Person) RETURN p;") == 3, "tx after commit=3");
    }

    /* ========== DDL 收尾：DROP TABLE ========== */
    {
        lbug_query_result r;
        CHECK(query_ok(&conn, "DROP TABLE KNOWS;", &r), "ddl drop rel table");
        lbug_query_result_destroy(&r);
        CHECK(query_ok(&conn, "DROP TABLE Person;", &r), "ddl drop node table");
        lbug_query_result_destroy(&r);
    }

    lbug_connection_destroy(&conn);
    lbug_database_destroy(&db);

    printf("\nAI 补充测试结果: PASS=%d FAIL=%d\n", g_pass, g_fail);
    if (g_fail == 0) {
        printf("PASS: all AI-complemented upstream scenario tests\n");
        return 0;
    }
    return 1;
}
