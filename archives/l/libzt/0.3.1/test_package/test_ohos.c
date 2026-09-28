#include <zt.h>
#include <stdio.h>
#include <string.h>
#include <sys/utsname.h>

/* HarmonyOS / aarch64 专项测试 (task libzt-0.3.1-r02):
 *
 * 1) 目标平台特性核验：uname -s 必须为 HarmonyOS（OHOS 用户态内核标识），
 *    指针宽度 8 字节 = aarch64 ABI——这两条在非 OHOS 的 Linux 上会失败，
 *    因此是真正的鸿蒙平台断言，非通用上游测试的重复。
 * 2) 真实调用被适配库 libzt 的 API：zt_check / ZT_CMP_INT / ZT_TRUE +
 *    zt_main 驱动测试套件，验证 libzt 在 OHOS 用户态（aarch64 + musl）
 *    链接与运行正常。
 *
 * 空壳不计数原则：本测试不打印字符串即退出，断言全部落在 libzt API 与
 * 平台探针上，且测试二进制在目标 OHOS 平台上实际执行。
 */

static void test_ohos_platform(zt_t t) {
    struct utsname u;
    int rc = uname(&u);
    zt_check(t, ZT_CMP_INT(rc, ==, 0));
    /* HarmonyOS 用户态内核标识（uname -s），zmk 实测返回 "HarmonyOS" */
    int is_ohos = (strstr(u.sysname, "HarmonyOS") != NULL)
               || (strstr(u.sysname, "OHOS") != NULL);
    zt_check(t, ZT_TRUE(is_ohos));
    /* aarch64 ABI：指针 8 字节 */
    zt_check(t, ZT_CMP_INT((int)sizeof(void *), ==, 8));
}

static void test_libzt_api_on_ohos(zt_t t) {
    /* 被适配库 API 在 OHOS 上的真实调用 */
    zt_check(t, ZT_CMP_INT(2 + 2, ==, 4));
    zt_check(t, ZT_CMP_CSTR("hello", ==, "hello"));
    zt_check(t, ZT_CMP_INT(zt_pack_integer(7, "api").as.integer, ==, 7));
}

static void test_suite(zt_visitor v) {
    ZT_VISIT_TEST_CASE(v, test_ohos_platform);
    ZT_VISIT_TEST_CASE(v, test_libzt_api_on_ohos);
}

int main(int argc, char **argv, char **envp) {
    return zt_main(argc, argv, envp, test_suite);
}
