/* 鸿蒙专项测试（HarmonyOS PC / aarch64-linux-ohos）：
 * 1. 验证 cester.h 在 OHOS clang15/musl 工具链下可编译链接；
 * 2. 验证 libcester 断言宏在 OHOS 运行时行为正确；
 * 3. 验证 POSIX 运行时路径（clock_gettime / 环境变量读取）在 OHOS 可用。 */

#include <exotic/cester.h>
#include <string.h>
#include <time.h>
#include <stdlib.h>

CESTER_TEST(ohos_toolchain_compile_link, inst,
    /* 编译链接本身即验证点：能在 OHOS 工具链下构建并链接该测试 */
    cester_assert_true(1 == 1);
)

CESTER_TEST(ohos_posix_clock_gettime, inst,
#if defined(__unix__) || defined(__linux__) || defined(__OHOS__)
    struct timespec ts;
    int rc = clock_gettime(CLOCK_MONOTONIC, &ts);
    cester_assert_int_eq(rc, 0);
    cester_assert_int_ge((int)ts.tv_sec, 0);
#else
    cester_assert_true(1);
#endif
)

CESTER_TEST(ohos_libc_musl_strlen, inst,
    cester_assert_int_eq((int)strlen("HarmonyOS"), 9);
    cester_assert_int_eq((int)strcmp("aarch64-linux-ohos", "aarch64-linux-ohos"), 0);
)

CESTER_TEST(ohos_runtime_env_getenv, inst,
    /* OHOS 下 getenv 应返回非 NULL（至少 PATH/HOME 等常见变量存在） */
    const char* path = getenv("PATH");
    cester_assert_not_null((void*)path);
)
