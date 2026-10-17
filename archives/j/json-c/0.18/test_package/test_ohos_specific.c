/*
 * test_ohos_specific.c — HarmonyOS 专项测试（json-c 0.18）
 *
 * 本测试独立于上游 ctest 用例与消费者冒烟测试，针对 HarmonyOS
 * 平台验证 json-c 公开 API 的以下能力：
 *   1) UTF-8 中文字符串的解析/序列化往返（locale/编码相关）
 *   2) 大 int64 数值的解析与获取（json-c 特有大整数处理路径）
 *   3) 嵌套对象/数组的迭代访问（公开遍历 API）
 *   4) json_object_get_type 类型判别
 *
 * 仅使用库导出的公开头文件（json-c/json.h）与公开 API，
 * 不包含库私有头文件，不调用内部符号。
 *
 * 编译：
 *   cc test_ohos_specific.c -I$PREFIX/include -L$PREFIX/lib -ljson-c
 * 运行：
 *   LD_LIBRARY_PATH=$PREFIX/lib ./test_ohos_specific
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <json-c/json.h>

static int failures = 0;

#define CHECK(cond, msg)                                          \
    do {                                                          \
        if (cond) {                                               \
            printf("PASS: %s\n", msg);                            \
        } else {                                                  \
            printf("FAIL: %s\n", msg);                            \
            failures++;                                           \
        }                                                         \
    } while (0)

/* 1) UTF-8 中文往返 */
static void test_utf8_roundtrip(void)
{
    const char *doc =
        "{\"message\":\"鸿蒙OS编译验证\",\"author\":\"适配执行端\","
        "\"tags\":[\"OHOS\",\"aarch64\",\"三方库\"],"
        "\"nested\":{\"note\":\"中文嵌套\"}}";
    struct json_object *parsed = json_tokener_parse(doc);
    CHECK(parsed != NULL, "UTF-8 中文文档解析");

    if (!parsed)
        return;

    struct json_object *msg = NULL;
    CHECK(json_object_object_get_ex(parsed, "message", &msg),
          "获取 message 字段");
    if (msg) {
        const char *s = json_object_get_string(msg);
        CHECK(s != NULL && strcmp(s, "鸿蒙OS编译验证") == 0,
              "message 字段内容为中文原文");
        printf("  message = %s\n", s ? s : "(null)");
    }

    /* 序列化后重新解析，验证往返一致 */
    const char *ser = json_object_to_json_string(parsed);
    CHECK(ser != NULL, "中文文档序列化");
    if (ser) {
        struct json_object *reparsed = json_tokener_parse(ser);
        CHECK(reparsed != NULL, "序列化结果可重新解析");
        if (reparsed) {
            struct json_object *m2 = NULL;
            json_object_object_get_ex(reparsed, "message", &m2);
            const char *s2 = m2 ? json_object_get_string(m2) : NULL;
            CHECK(s2 != NULL && strcmp(s2, "鸿蒙OS编译验证") == 0,
                  "往返后 message 仍为中文原文");
            json_object_put(reparsed);
        }
    }
    json_object_put(parsed);
}

/* 2) 大 int64 数值 */
static void test_int64_large(void)
{
    struct json_object *o = json_tokener_parse("{\"big\": 9223372036854775807}");
    CHECK(o != NULL, "大 int64 文档解析");

    if (!o)
        return;

    struct json_object *big = NULL;
    CHECK(json_object_object_get_ex(o, "big", &big), "获取 big 字段");
    if (big) {
        CHECK(json_object_get_type(big) == json_type_int,
              "big 字段类型为 json_type_int");
        int64_t v = json_object_get_int64(big);
        CHECK(v == 9223372036854775807LL, "int64 最大值精确读取");
        printf("  big = %lld\n", (long long)v);

        /* 写入并序列化，验证数值不被截断 */
        json_object_set_int64(big, -9223372036854775807LL - 1);
        const char *ser = json_object_to_json_string(o);
        CHECK(ser != NULL && strstr(ser, "-9223372036854775808") != NULL,
              "int64 最小值写入并完整序列化");
    }
    json_object_put(o);
}

/* 3) 嵌套对象/数组迭代 */
static void test_nested_iteration(void)
{
    struct json_object *root = json_tokener_parse(
        "{\"list\":[{\"id\":1,\"name\":\"alpha\"},"
        "{\"id\":2,\"name\":\"beta\"},{\"id\":3,\"name\":\"gamma\"}]}");
    CHECK(root != NULL, "嵌套数组文档解析");

    if (!root)
        return;

    struct json_object *list = NULL;
    CHECK(json_object_object_get_ex(root, "list", &list), "获取 list 字段");
    if (list) {
        CHECK(json_object_get_type(list) == json_type_array,
              "list 类型为 json_type_array");
        int len = json_object_array_length(list);
        CHECK(len == 3, "数组长度 3");
        printf("  list length = %d\n", len);

        int sum = 0;
        int i;
        for (i = 0; i < len; i++) {
            struct json_object *item = json_object_array_get_idx(list, i);
            if (!item || json_object_get_type(item) != json_type_object)
                continue;
            struct json_object *id = NULL;
            if (json_object_object_get_ex(item, "id", &id))
                sum += (int)json_object_get_int64(id);
        }
        CHECK(sum == 6, "迭代累加 id 总和为 6");
        printf("  sum(id) = %d\n", sum);
    }
    json_object_put(root);
}

int main(void)
{
    printf("=== json-c 0.18 HarmonyOS 专项测试 ===\n");
    printf("platform: %s\n", "OHOS aarch64");
    test_utf8_roundtrip();
    test_int64_large();
    test_nested_iteration();
    printf("===========================================\n");
    if (failures == 0) {
        printf("test_ohos_specific: ALL PASS\n");
        return 0;
    }
    printf("test_ohos_specific: %d FAILURE(S)\n", failures);
    return 1;
}
