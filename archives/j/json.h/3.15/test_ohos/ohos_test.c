/* OHOS 专项测试：通过公开 API 验证 json.h 在 HarmonyOS PC (armv8, OHOS clang)
 * 平台上的完整功能与可观察结果（与上游 utest 套件、test_package 消费者用例
 * 分别计数）。
 *
 * 验证点：
 *   1. json_parse 基础解析：对象/数组/字符串/数字/布尔/空
 *   2. JSON5 特性：allow_c_style_comments / allow_trailing_comma /
 *      allow_single_quoted_strings / allow_unquoted_keys
 *   3. json_extract_value DOM 抽取
 *   4. 错误输入返回 NULL（稳健性）
 *   5. 自定义分配器钩子（allocator callback）与 json_parse_ex
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "json.h"

static int alloc_calls = 0;

static void *counting_alloc(void *ud, size_t size) {
    (void)ud;
    alloc_calls++;
    return malloc(size);
}

static void counting_free(void *ud, void *ptr) {
    (void)ud;
    free(ptr);
}

#define CHECK(cond, msg) do { \
    if (!(cond)) { \
        fprintf(stderr, "OHOS test FAILED: %s (line %d)\n", msg, __LINE__); \
        return 1; \
    } \
} while (0)

static int test_basic_object(void) {
    const char *src = "{\"name\":\"json.h\",\"version\":315,\"pi\":3.14,"
                      "\"ok\":true,\"no\":false,\"nil\":null,"
                      "\"list\":[1,2,3],\"nested\":{\"a\":\"b\"}}";
    struct json_value_s *root = json_parse(src, strlen(src));
    CHECK(root != NULL, "basic parse returned NULL");
    CHECK(root->type == json_type_object, "root not object");
    struct json_object_s *obj = (struct json_object_s *)root->payload;
    int fields = 0;
    for (struct json_object_element_s *e = obj->start; e; e = e->next) {
        fields++;
    }
    CHECK(fields == 8, "object field count mismatch");
    free(root);
    printf("OHOS basic object parse: PASS (8 fields)\n");
    return 0;
}

static int test_json5_features(void) {
    /* C 风格注释 + 尾逗号 + 单引号字符串 + 裸键 */
    const char *src = "{key1:'single', "
                      "/* comment */ key2: 42, }";
    size_t flags = (size_t)json_parse_flags_allow_c_style_comments |
                   (size_t)json_parse_flags_allow_trailing_comma |
                   (size_t)json_parse_flags_allow_single_quoted_strings |
                   (size_t)json_parse_flags_allow_unquoted_keys;
    struct json_value_s *root =
        json_parse_ex(src, strlen(src), flags, NULL, NULL, NULL);
    CHECK(root != NULL, "json5 parse returned NULL");
    CHECK(root->type == json_type_object, "json5 root not object");
    struct json_object_s *obj = (struct json_object_s *)root->payload;
    int fields = 0;
    for (struct json_object_element_s *e = obj->start; e; e = e->next) {
        fields++;
    }
    CHECK(fields == 2, "json5 object field count mismatch");
    free(root);
    printf("OHOS json5 features parse: PASS (2 fields)\n");
    return 0;
}

static int test_extract_and_failure(void) {
    const char *src = "{\"outer\":{\"inner\":[10,20]}}";
    struct json_value_s *root = json_parse(src, strlen(src));
    CHECK(root != NULL, "nested parse returned NULL");
    /* json_extract_value: 从已解析 DOM 中抽取一个子值（独立分配） */
    struct json_object_s *obj = (struct json_object_s *)root->payload;
    struct json_object_element_s *outer = obj->start;
    CHECK(outer != NULL, "no outer element");
    struct json_value_s *outer_val = outer->value;
    struct json_object_s *inner_obj = (struct json_object_s *)outer_val->payload;
    struct json_object_element_s *inner = inner_obj->start;
    CHECK(inner != NULL, "no inner element");
    struct json_value_s *extracted = json_extract_value(inner->value);
    CHECK(extracted != NULL, "extract returned NULL");
    CHECK(extracted->type == json_type_array, "extracted value not array");
    free(extracted);
    free(root);

    /* 错误输入：不合法 JSON 应返回 NULL */
    struct json_value_s *bad = json_parse("{invalid", 8);
    CHECK(bad == NULL, "invalid json should return NULL");
    struct json_value_s *bad2 = json_parse("[1,2,", 5);
    CHECK(bad2 == NULL, "truncated json should return NULL");
    printf("OHOS extract + error handling: PASS\n");
    return 0;
}

static int test_allocator_hook(void) {
    const char *src = "[1,2,3,4,5]";
    alloc_calls = 0;
    struct json_parse_result_s result;
    struct json_value_s *root = json_parse_ex(src, strlen(src),
                                              (size_t)json_parse_flags_default,
                                              NULL, NULL, &result);
    CHECK(root != NULL, "allocator parse returned NULL");
    CHECK(result.error == (size_t)json_parse_error_none,
          "unexpected parse error");
    /* 自定 allocator 版本 */
    alloc_calls = 0;
    struct json_value_s *root2 = json_parse_ex(src, strlen(src),
                                               (size_t)json_parse_flags_default,
                                               counting_alloc, NULL,
                                               NULL);
    CHECK(root2 != NULL, "custom allocator parse returned NULL");
    CHECK(alloc_calls > 0, "custom allocator hook not invoked");
    free(root2);
    free(root);
    printf("OHOS allocator hook: PASS\n");
    return 0;
}

int main(void) {
    if (test_basic_object()) return 1;
    if (test_json5_features()) return 1;
    if (test_extract_and_failure()) return 1;
    if (test_allocator_hook()) return 1;
    printf("ALL OHOS json.h special tests passed\n");
    return 0;
}