/*
 * test_ohos.c — c-vtapi HarmonyOS 专项测试（真实可执行,非空测试）
 *
 * 验证内容（全部离线,不依赖 VirusTotal 外网/API key,在 OHOS aarch64 原生运行）:
 *  1. VtResponse_fromJSONstr 使用 jansson 解析 VirusTotal 风格 JSON 响应;
 *  2. VtResponse_getIntValue / getString 字段提取正确;
 *  3. VtResponse_toJSONstr 重新序列化非空;
 *  4. VtObject refcount 语义: VtObject_get 递增 / VtObject_put 递减,归零后释放且指针置 NULL;
 *  5. VtApiPage 对象生命周期与 setApiKey 内存路径。
 */
#include <stdio.h>
#include <string.h>

#include "VtResponse.h"
#include "VtObject.h"
#include "VtApiPage.h"

static int checks = 0;

#define CHECK(cond, msg) do {                                    \
    if (cond) { checks++; }                                      \
    else {                                                       \
        fprintf(stderr, "FAIL: %s (line %d)\n", msg, __LINE__);  \
        return 1;                                                \
    }                                                            \
} while (0)

int main(void) {
    /* 1-3: VtResponse JSON 解析/提取/序列化（离线） */
    struct VtResponse *resp = VtResponse_new();
    CHECK(resp != NULL, "VtResponse_new");

    const char *sample =
        "{\"response_code\":1,\"verbose_msg\":\"Scan request successfully "
        "queued, come back later for the report\",\"resource\":"
        "\"99017f6eebbac24f351417dd4d0edcad\"}";
    CHECK(VtResponse_fromJSONstr(resp, sample) == 0, "VtResponse_fromJSONstr");

    int code = -1;
    CHECK(VtResponse_getIntValue(resp, "response_code", &code) == 0,
          "VtResponse_getIntValue");
    CHECK(code == 1, "response_code == 1");

    char *msg = VtResponse_getString(resp, "verbose_msg");
    CHECK(msg != NULL && strstr(msg, "queued") != NULL,
          "VtResponse_getString verbose_msg");

    char *re = VtResponse_toJSONstr(resp, 0);
    CHECK(re != NULL && re[0] == '{', "VtResponse_toJSONstr non-empty");

    /* 4: VtObject refcount 语义（上游契约：put 总是把调用者指针置 NULL，
     * 对象在 refcount 归零时才真正释放——用双别名验证） */
    struct VtApiPage *page = VtApiPage_new();
    CHECK(page != NULL, "VtApiPage_new");
    CHECK(page->refcount == 1, "refcount == 1 after new");

    VtObject_get((struct VtObject *)page);   /* ref 2 */
    CHECK(page->refcount == 2, "refcount == 2 after get");

    struct VtApiPage *alias = page;          /* 第二个别名（未 bump ref） */
    VtObject_put((struct VtObject **)(void *)&page);  /* ref 1：指针被置 NULL，对象仍存活 */
    CHECK(page == NULL, "caller pointer NULLed by put");
    CHECK(alias != NULL && alias->refcount == 1, "object alive via alias at ref 1");

    VtObject_put((struct VtObject **)(void *)&alias);  /* ref 0：真正释放 */
    CHECK(alias == NULL, "object freed and NULLed at ref 0");

    /* 5: setApiKey 内存路径 */
    page = VtApiPage_new();
    CHECK(page != NULL, "VtApiPage_new #2");
    VtApiPage_setApiKey(page, "ohos-test-api-key");
    CHECK(strcmp(page->api_key, "ohos-test-api-key") == 0,
          "setApiKey roundtrip");
    VtApiPage_put(&page);
    CHECK(page == NULL, "VtApiPage_put #2");

    printf("PASS: c-vtapi OHOS-specific test, %d checks passed\n", checks);
    return 0;
}