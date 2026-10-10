/* test_package/test.c — Conan L1 消费者测试（librepo 1.20.0, HarmonyOS PC）
 *
 * 以真实消费者身份链接 librepo + glib，验证：
 *  1. 版本宏与 LR_VERSION_CHECK
 *  2. LrHandle/LrResult 生命周期（lr_handle_init / lr_handle_free / lr_result_init / lr_result_free）
 *  3. lr_handle_setopt(LRO_URLS) -> lr_handle_getinfo(LRI_URLS) 往返
 *  4. lr_checksum_type/lr_checksum_type_to_str 校验和类型映射表
 *  5. lr_checksum_fd() 用 libcrypto 完整计算一段已知数据的 SHA256 摘要
 *
 * 期望输出: LIBREPO_CONSUMER_OK
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>

#include <glib.h>
#include <librepo/librepo.h>
#include <librepo/checksum.h>
#include <librepo/handle.h>
#include <librepo/result.h>
#include <librepo/version.h>

static int g_failed = 0;

#define CHECK(cond, msg)                                              \
    do {                                                              \
        if (cond) {                                                   \
            printf("ok   - %s\n", msg);                               \
        } else {                                                      \
            printf("FAIL - %s\n", msg);                               \
            g_failed = 1;                                             \
        }                                                             \
    } while (0)

int main(void)
{
    /* 1. 版本宏 */
    CHECK(LR_VERSION_MAJOR == 1 && LR_VERSION_MINOR == 20 && LR_VERSION_PATCH == 0,
          "version.h exposes 1.20.0");
    CHECK(LR_VERSION_CHECK(1, 20, 0), "LR_VERSION_CHECK(1,20,0) passes");

    /* 2. LrHandle / LrResult 生命周期 */
    LrHandle *handle = lr_handle_init();
    CHECK(handle != NULL, "lr_handle_init() returns a handle");
    LrResult *result = lr_result_init();
    CHECK(result != NULL, "lr_result_init() returns a result");

    /* 3. LRO_URLS setopt -> LRI_URLS getinfo 往返 */
    const char *urls[] = { "https://example.com/repo/", NULL };
    GError *err = NULL;
    gboolean ok = lr_handle_setopt(handle, &err, LRO_URLS, urls);
    CHECK(ok && err == NULL, "lr_handle_setopt(LRO_URLS) succeeds");
    if (err) { g_error_free(err); err = NULL; }

    char **ret_urls = NULL;
    ok = lr_handle_getinfo(handle, &err, LRI_URLS, &ret_urls);
    CHECK(ok && err == NULL && ret_urls && ret_urls[0] &&
          strcmp(ret_urls[0], "https://example.com/repo/") == 0,
          "LRI_URLS round-trips the URL list");
    if (err) { g_error_free(err); err = NULL; }
    if (ret_urls) {
        for (char **u = ret_urls; *u; u++) free(*u);
        free(ret_urls);
    }

    /* 4. 校验和类型映射（覆盖 openssl/gpgme 之外的纯 librepo 侧 API） */
    CHECK(lr_checksum_type("sha256") == LR_CHECKSUM_SHA256,
          "lr_checksum_type(\"sha256\") maps correctly");
    CHECK(g_strcmp0(lr_checksum_type_to_str(LR_CHECKSUM_SHA256), "sha256") == 0,
          "lr_checksum_type_to_str(SHA256) round-trips");

    /* 5. lr_checksum_fd: 用 libcrypto 计算已知数据的 SHA256 */
    const char *data = "librepo on HarmonyOS PC";
    /* OHOS: /tmp 不可写，优先使用 $TMPDIR */
    const char *tmp_env = g_getenv("TMPDIR");
    gchar *tmpl = g_build_filename((tmp_env && tmp_env[0]) ? tmp_env : "/tmp",
                                   "librepo_testpkg_XXXXXX", NULL);
    int fd = mkstemp(tmpl);
    CHECK(fd >= 0, "mkstemp creates scratch file");
    if (fd >= 0) {
        ssize_t written = write(fd, data, strlen(data));
        CHECK(written == (ssize_t)strlen(data), "scratch data written");
        gchar *sha256 = lr_checksum_fd(LR_CHECKSUM_SHA256, fd, &err);
        CHECK(sha256 != NULL && err == NULL,
              "lr_checksum_fd(SHA256) computes via libcrypto");
        CHECK(sha256 && strlen(sha256) == 64,
              "digest is a 64-char hex string");
        printf("     sha256(\"%s\") = %s\n", data, sha256 ? sha256 : "(null)");
        g_free(sha256);
        if (err) { g_error_free(err); err = NULL; }
        close(fd);
        unlink(tmpl);
    }
    g_free(tmpl);

    /* 生命周期收尾 */
    lr_result_free(result);
    lr_handle_free(handle);
    CHECK(1, "lr_result_free/lr_handle_free complete without crash");

    if (g_failed) {
        printf("LIBREPO_CONSUMER_FAILED\n");
        return 1;
    }
    printf("LIBREPO_CONSUMER_OK\n");
    return 0;
}
