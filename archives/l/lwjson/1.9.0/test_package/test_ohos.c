#include <stdio.h>
#include <string.h>
#include <assert.h>
#include "lwjson/lwjson.h"

/* HarmonyOS / aarch64 专项测试 (task lwjson-1.9.0-r01-pc1-3):
 *
 * 1) UTF-8 多字节字符串：鸿蒙系统默认 UTF-8 语言环境，验证含中文与 emoji
 *    的字符串经 lwjson 解析后 token_value 字节数不变、内容一致（上游
 *    test 只用 ASCII 样例，未覆盖多字节语义）。
 * 2) 令牌预算守恒：lwjson 面向嵌入式/受限内存场景，解析后 token 占用
 *    必须严格等于输入结构所需数（lwjson_get_tokens_used），验证
 *    aarch64 上无额外令牌泄漏——上游测试未做该断言。
 * 3) 深层嵌套数组迭代：多层数组/对象混合结构逐层遍历（业务上常见的
 *    配置树），验证内存受限下对深 JSON 的处理正确性。
 *
 * 注意：副作用调用（lwjson_init/parse/free）放在 assert() 之外，保证
 * -DNDEBUG（CI Release）下仍真实执行。
 */

static lwjson_token_t g_tokens[256];

static void test_utf8_roundtrip(void) {
    const char* json = "{\"msg\":\"鸿蒙PC平台适配测试-中文⚡\",\"n\":1}";
    lwjson_t lwobj;
    lwjsonr_t r = lwjson_init(&lwobj, g_tokens, sizeof(g_tokens) / sizeof(g_tokens[0]));
    assert(r == lwjsonOK);
    r = lwjson_parse(&lwobj, json);
    assert(r == lwjsonOK);

    const lwjson_token_t* tok = lwjson_find(&lwobj, "msg");
    assert(tok != NULL && tok->type == LWJSON_TYPE_STRING);

    size_t len = 0;
    const char* s = lwjson_get_val_string(tok, &len);
    assert(s != NULL);
    /* "鸿蒙PC平台适配测试-中文⚡" 的 UTF-8 字节数：
       8 个 CJK 字符 ×3 + "PC"×2 + "-"×1 + "中文"×6 + emoji×4 = 36 */
    size_t expected = strlen("鸿蒙PC平台适配测试-中文⚡");
    assert(len == expected);
    assert(memcmp(s, "鸿蒙PC平台适配测试-中文⚡", expected) == 0);

    lwjson_free(&lwobj);
    printf("test_utf8_roundtrip: %zu UTF-8 bytes round-trip OK\n", expected);
}

static void test_token_budget(void) {
    /* 输入结构：object { key, arr[3] }。
       lwjson 的根对象复用内嵌 first_token，因此 token 占用 =
       2 个 key + 1 个 array + 3 个 number = 6（探针实测 6）。 */
    const char* json = "{\"key\":\"v\",\"arr\":[1,2,3]}";
    lwjson_t lwobj;
    lwjsonr_t r = lwjson_init(&lwobj, g_tokens, sizeof(g_tokens) / sizeof(g_tokens[0]));
    assert(r == lwjsonOK);
    r = lwjson_parse(&lwobj, json);
    assert(r == lwjsonOK);
    size_t used = lwjson_get_tokens_used(&lwobj);
    assert(used == 6);
    lwjson_free(&lwobj);
    printf("test_token_budget: %zu tokens used (expected 6) OK\n", used);
}

static void test_deep_nesting(void) {
    const char* json =
        "{\"a\":{\"b\":{\"c\":{\"d\":{\"e\":{\"f\":[{\"x\":1},{\"x\":2}]}}}}}}";
    lwjson_t lwobj;
    lwjsonr_t r = lwjson_init(&lwobj, g_tokens, sizeof(g_tokens) / sizeof(g_tokens[0]));
    assert(r == lwjsonOK);
    r = lwjson_parse(&lwobj, json);
    assert(r == lwjsonOK);

    const lwjson_token_t* tok = lwjson_find(&lwobj, "a.b.c.d.e.f");
    assert(tok != NULL && tok->type == LWJSON_TYPE_ARRAY);

    int sum = 0;
    const lwjson_token_t* child = lwjson_get_first_child(tok);
    while (child != NULL) {
        const lwjson_token_t* x = lwjson_find_ex(&lwobj, child, "x");
        assert(x != NULL && x->type == LWJSON_TYPE_NUM_INT);
        sum += (int)lwjson_get_val_int(x);
        child = child->next;
    }
    assert(sum == 3);

    lwjson_free(&lwobj);
    printf("test_deep_nesting: 6-level nesting + array of objects sum=%d OK\n", sum);
}

int main(void) {
    test_utf8_roundtrip();
    test_token_budget();
    test_deep_nesting();
    printf("lwjson 1.9.0 HarmonyOS/aarch64 specialty tests: ALL PASS\n");
    return 0;
}