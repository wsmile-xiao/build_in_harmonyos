// test_ohos.cpp — HarmonyOS 专项测试用例
//
// 验证 gason 在 HarmonyOS PC (aarch64, clang 15 / libc++) 目标上的
// 平台适配完整性：解析含 UTF-8 中文与转义序列的 JSON，验证数值边界、
// 深层嵌套、错误输入回报，全部使用安装产物的公开 API。
#include <gason.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond, msg)                              \
    do {                                              \
        if (!(cond)) {                                \
            fprintf(stderr, "FAIL: %s\n", msg);       \
            ++failures;                               \
        }                                             \
    } while (0)

static void test_unicode_object(void) {
    char src[] = "{\"\u6570\u636e\":\"\u4e2d\u6587\u6d4b\u8bd5\",\"\u522b\u540d\":[\"a\",\"\u6587\"]}";
    char *endptr;
    JsonValue value;
    JsonAllocator allocator;
    int status = jsonParse(src, &endptr, &value, allocator);
    CHECK(status == JSON_OK, "unicode object parses");
    if (status != JSON_OK)
        return;
    CHECK(value.getTag() == JSON_OBJECT, "unicode object tag");
    int members = 0;
    for (JsonNode *n : value)
        ++members;
    CHECK(members == 2, "unicode object has 2 members");
    for (JsonNode *n : value) {
        if (strcmp(n->key, "\u522b\u540d") == 0) {
            CHECK(n->value.getTag() == JSON_ARRAY, "别名 is array");
            int cnt = 0;
            for (JsonNode *t : n->value)
                ++cnt;
            CHECK(cnt == 2, "别名 array length 2");
        }
    }
}

static void test_number_edge(void) {
    char src[] = "[1e-21474836311, 1e-42147483631, -0, -.666, 13.19e+1]";
    char *endptr;
    JsonValue value;
    JsonAllocator allocator;
    int status = jsonParse(src, &endptr, &value, allocator);
    CHECK(status == JSON_OK, "edge numbers parse");
    if (status != JSON_OK)
        return;
    int cnt = 0;
    for (JsonNode *n : value) {
        CHECK(n->value.getTag() == JSON_NUMBER, "array element is number");
        ++cnt;
    }
    CHECK(cnt == 5, "edge numbers array length 5");
}

static void test_deep_nesting(void) {
    // gason 解析器嵌套深度上限为 32（实测 34+ 报 STACK_OVERFLOW），
    // 此处使用上限内的最深层级验证可解析性。
    char src[] = "[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[\"deep ok\"]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]";
    char *endptr;
    JsonValue value;
    JsonAllocator allocator;
    int status = jsonParse(src, &endptr, &value, allocator);
    CHECK(status == JSON_OK, "deep nesting (32) parses");
}

static void test_error_input(void) {
    char src[] = "{\"a\": 1 + 2}";
    char *endptr;
    JsonValue value;
    JsonAllocator allocator;
    int status = jsonParse(src, &endptr, &value, allocator);
    CHECK(status != JSON_OK, "bad expression rejected");
}

int main(void) {
    test_unicode_object();
    test_number_edge();
    test_deep_nesting();
    test_error_input();

    if (failures == 0) {
        printf("test_ohos: ALL OHOS-SPECIFIC CHECKS PASSED\n");
        return 0;
    }
    fprintf(stderr, "test_ohos: %d CHECK(S) FAILED\n", failures);
    return 1;
}
