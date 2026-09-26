/* Consumer smoke test for libnm 1.58.0 on HarmonyOS PC (OHOS / musl).
 *
 * Cases:
 *   1) headers-and-version  —— #include <NetworkManager.h>，
 *      NM_CHECK_VERSION(1,58,0) 编译期断言 + nm_utils_version() 运行期核对。
 *   2) uuid-api             —— nm_utils_uuid_generate() 生成合法 v4 UUID。
 *   3) ohos-consumer-smoke  —— 鸿蒙消费者可行性：对包内物化后的运行时
 *      SONAME（libnm.so.0，规则文件、自签名）做 dlopen(RTLD_NOW) +
 *      dlsym("nm_utils_version")，与直链符号取值一致性核对，证明
 *      OHOS musl 动态加载器可以加载并消费该包（E316 实体化闭环）。
 */
#include <NetworkManager.h>

#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if !NM_CHECK_VERSION(1, 58, 0)
#error "libnm >= 1.58.0 headers required"
#endif

static int g_checks = 0;
static int g_failures = 0;

static void
report(int ok, const char *name, const char *detail)
{
    printf("%s: %s%s%s\n", ok ? "ok" : "FAIL", name, detail ? " - " : "", detail ? detail : "");
    g_checks++;
    if (!ok)
        g_failures++;
}

int
main(int argc, char **argv)
{
    /* 1) headers-and-version */
    {
        char detail[128];
        guint version = nm_utils_version();
        /* NM 的版本号是位打包：NM_ENCODE_VERSION(major,minor,micro)
         *   = (major << 16) | (minor << 8) | micro
         * 故 1.58.0 = 0x013A00 = 80384（并非十进制 1058000）。与头文件宏
         * NM_VERSION_1_58 比较，核对运行期与头文件版本一致。 */
        snprintf(detail, sizeof(detail), "nm_utils_version()=%u expected=%d",
                 version, (int) NM_VERSION_1_58);
        report(version == (guint) NM_VERSION_1_58, "headers-and-version", detail);
    }

    /* 2) uuid-api */
    {
        char *uuid = nm_utils_uuid_generate();
        report(uuid && strlen(uuid) == 36 && uuid[14] == '4', "uuid-api", uuid);
        g_free(uuid);
    }

    /* 3) ohos-consumer-smoke —— 鸿蒙消费者用例 */
    {
        const char *soname_path = argc > 1 ? argv[1] : getenv("LIBNM_TEST_SONAME");
        char detail[256];
        void *handle;
        guint (*version_fn)(void);

        snprintf(detail, sizeof(detail), "soname=%s", soname_path ? soname_path : "(unset)");
        report(soname_path && soname_path[0] == '/', "ohos-consumer-smoke/arg", detail);
        if (!soname_path || soname_path[0] != '/')
            return g_failures ? 1 : 0;

        handle = dlopen(soname_path, RTLD_NOW | RTLD_LOCAL);
        snprintf(detail, sizeof(detail), "dlopen(%s): %s", soname_path, handle ? "OK" : dlerror());
        report(handle != NULL, "ohos-consumer-smoke/dlopen", detail);

        if (handle) {
            version_fn = (guint (*)(void)) dlsym(handle, "nm_utils_version");
            snprintf(detail, sizeof(detail), "dlsym nm_utils_version -> %p", (void *)version_fn);
            report(version_fn != NULL, "ohos-consumer-smoke/dlsym", detail);
            if (version_fn) {
                snprintf(detail, sizeof(detail), "dlopened nm_utils_version()=%u (direct %u)",
                         version_fn(), nm_utils_version());
                report(version_fn() == nm_utils_version(), "ohos-consumer-smoke/symbol-consistency", detail);
            }
            dlclose(handle);
        }
    }

    /* 汇总：分别打印「执行数」与「失败数」，避免把失败数误读成未执行任何检查
     *（AI Review P3：旧版只打印失败数却标成 check(s)）。 */
    printf("%d check(s) run, %d failure(s): %s\n",
           g_checks, g_failures, g_failures ? "FAILED" : "PASSED");
    return g_failures ? 1 : 0;
}
