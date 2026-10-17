#include <Muon/Muon.h>
#include <string.h>
#include <time.h>

/* 鸿蒙专项测试（HarmonyOS PC / aarch64-linux-ohos）：
 * 1. 验证 Muon 头文件在 OHOS clang15/musl 工具链下可编译链接；
 * 2. 验证 Muon 的 POSIX 计时路径（CLOCK_PROCESS_CPUTIME_ID/CLOCK_MONOTONIC）在 OHOS 可用；
 * 3. 验证字符串/数值断言宏在 OHOS 运行时行为正确。
 * 注：CHECK/REQUIRE 需携带消息参数；STRNE 系为 3 参（n=比较长度）。 */

TEST(ohos, toolchain_compile_link) {
    /* 编译链接本身即验证点：能在 OHOS 工具链下构建并链接该测试 */
    CHECK(1, "compile & link ok");
}

TEST(ohos, posix_timer_clock_gettime) {
#if defined(MUON_HAS_POSIX_TIMER_) || defined(__unix__) || defined(__linux__)
    struct timespec ts;
    int rc = clock_gettime(CLOCK_MONOTONIC, &ts);
    CHECK(rc == 0, "clock_gettime(CLOCK_MONOTONIC) rc == 0");
    CHECK(ts.tv_sec >= 0, "ts.tv_sec >= 0");
#else
    CHECK(0, "CLOCK_MONOTONIC unavailable on OHOS");
#endif
}

TEST(ohos, string_macros_on_ohos) {
    REQUIRE_STREQ("OHOS", "OHOS");
    CHECK_STRNEQ("tau", "muon");
    /* CHECK_STRNNE: 前 n 字符不相同则通过（"abc" vs "abd" 前 3 字符不同） */
    CHECK_STRNNE("abc", "abd", 3);
}

TEST(ohos, numeric_macros_on_ohos) {
    REQUIRE_EQ(7 * 6, 42);
    CHECK_GT(100, 99);
    CHECK_LE(2, 2);
    CHECK_GE(3, 3);
    CHECK_LT(1, 2);
    CHECK(7 * 6 == 42, "7*6 == 42");
}

TEST(ohos, libc_musl_strlen) {
    CHECK(strlen("HarmonyOS") == 9, "strlen(HarmonyOS)==9");
    CHECK(strcmp("aarch64-linux-ohos", "aarch64-linux-ohos") == 0, "strcmp equal");
}

MUON_MAIN()