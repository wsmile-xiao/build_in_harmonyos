/*
 * test.c — libideviceactivation 消费者测试（Conan L1）
 *
 * 真实调用被测包 API（不做 print-only 空壳）：
 *   - libplist 路径   : 请求字段 dict 的 set/get 往返、get_fields 返回 plist dict
 *   - libcurl 路径    : idevice_activation_drm_handshake_request_new() 生成默认握手 URL
 *   - libxml2 路径    : idevice_activation_response_new_from_html() 解析 HTML 并做 XPath 判定
 *   - 鸿蒙特有断言    : 运行环境为目标平台 OHOS/aarch64（uname 系统标识）
 *
 * 全部用例均不需要物理 iOS 设备。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/utsname.h>

#include <plist/plist.h>
#include <libideviceactivation.h>

static int failures = 0;
static int checks = 0;

#define CHECK(cond, name) do {                       \
    checks++;                                        \
    if (cond) {                                      \
        printf("  [PASS] %s\n", name);               \
    } else {                                         \
        printf("  [FAIL] %s\n", name);               \
        failures++;                                  \
    }                                                \
} while (0)

int main(void)
{
    idevice_activation_request_t req = NULL;
    idevice_activation_response_t resp = NULL;
    idevice_activation_error_t rc = IDEVICE_ACTIVATION_E_SUCCESS;
    const char *url = NULL;
    char *val = NULL;
    plist_t fields = NULL;
    struct utsname un;

    printf("== libideviceactivation consumer test ==\n");
    idevice_activation_set_debug_level(1);

    /* ---- libcurl-backed: DRM handshake request creation ---------------- */
    rc = idevice_activation_drm_handshake_request_new(
             IDEVICE_ACTIVATION_CLIENT_MOBILE_ACTIVATION, &req);
    CHECK(rc == IDEVICE_ACTIVATION_E_SUCCESS && req != NULL,
          "drm_handshake_request_new() == SUCCESS");

    idevice_activation_request_get_url(req, &url);
    CHECK(url != NULL && strncmp(url, "https://", 8) == 0,
          "default activation service URL is https");

    /* ---- libplist-backed: field round-trip ----------------------------- */
    idevice_activation_request_set_field(req, "ActivationRandomness",
                                         "0123456789abcdef");
    idevice_activation_request_get_field(req, "ActivationRandomness", &val);
    CHECK(val != NULL && strcmp(val, "0123456789abcdef") == 0,
          "request set/get field round-trip (libplist)");
    free(val);
    val = NULL;

    idevice_activation_request_get_fields(req, &fields);
    CHECK(fields != NULL && plist_get_node_type(fields) == PLIST_DICT,
          "request_get_fields() returns a plist dict");
    if (fields) {
        plist_free(fields);
        fields = NULL;
    }

    /* ---- custom service URL override ----------------------------------- */
    idevice_activation_request_set_url(req, "https://example.invalid/activate");
    idevice_activation_request_get_url(req, &url);
    CHECK(url != NULL && strcmp(url, "https://example.invalid/activate") == 0,
          "request_set_url() overrides activation service URL");

    idevice_activation_request_free(req);
    req = NULL;

    /* ---- response lifecycle -------------------------------------------- */
    rc = idevice_activation_response_new(&resp);
    CHECK(rc == IDEVICE_ACTIVATION_E_SUCCESS && resp != NULL,
          "response_new() == SUCCESS");
    CHECK(idevice_activation_response_has_errors(resp) == 0,
          "fresh response has no errors");
    idevice_activation_response_free(resp);
    resp = NULL;

    /* ---- libxml2-backed: HTML response parsing + XPath ------------------ */
    rc = idevice_activation_response_new_from_html(
             "<html><body><p>hello</p></body></html>", &resp);
    CHECK(rc == IDEVICE_ACTIVATION_E_SUCCESS && resp != NULL,
          "response_new_from_html(plain) == SUCCESS (libxml2 html parser)");
    CHECK(idevice_activation_response_has_errors(resp) == 1,
          "plain html without plist payload sets has_errors == 1");
    idevice_activation_response_free(resp);
    resp = NULL;

    rc = idevice_activation_response_new_from_html(
             "<html><body><input name=\"isAuthRequired\" value=\"true\"/></body></html>",
             &resp);
    CHECK(rc == IDEVICE_ACTIVATION_E_SUCCESS && resp != NULL,
          "response_new_from_html(auth) == SUCCESS");
    CHECK(idevice_activation_response_is_authentication_required(resp) == 1,
          "XPath //input[@name='isAuthRequired'] detected on OHOS libxml2");
    idevice_activation_response_free(resp);
    resp = NULL;

    /* ---- OHOS-specific: target platform identity ------------------------ */
    /* 先 memset 再 uname：uname() 失败时不得读取未初始化的 struct utsname
       （AI 检视意见 P3，2026-09-22）。失败时相关断言按 fail-closed 处理。 */
    memset(&un, 0, sizeof(un));
    int uname_ok = (uname(&un) == 0);
    CHECK(uname_ok, "uname() available");
    printf("   [INFO] sysname=%s machine=%s release=%s\n",
           uname_ok ? un.sysname : "(uname failed)",
           uname_ok ? un.machine : "(uname failed)",
           uname_ok ? un.release : "(uname failed)");
    CHECK(uname_ok && strcmp(un.sysname, "HarmonyOS") == 0,
          "OHOS case: runtime sysname == HarmonyOS");
    CHECK(uname_ok && strcmp(un.machine, "aarch64") == 0,
          "OHOS case: runtime machine == aarch64");
    CHECK(sizeof(void *) == 8,
          "OHOS case: 64-bit aarch64 pointer model");

    printf("== checks: %d, failures: %d ==\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
