#include <Muon/Muon.h>
#include <string.h>

/* test_package: 通过安装后的公开头文件 <Muon/Muon.h> 使用 Muon 框架，
 * 验证第三方使用者可编译、链接并实际运行断言（R34：禁止空壳 print）。
 * 注：Muon 的 CHECK/REQUIRE 宏需携带消息参数（__VA_ARGS__），
 *     CHECK_STRNE/REQUIRE_STRNE 为 3 参（n=比较长度）。 */

TEST(c_consumer, CHECK_TRUE) {
    CHECK(1 == 1, "1 == 1");
}

TEST(c_consumer, REQUIRE_EQ) {
    REQUIRE_EQ(2 + 3, 5);
}

TEST(c_consumer, REQUIRE_STREQ) {
    REQUIRE_STREQ("muon", "muon");
}

TEST(c_consumer, CHECK_GT) {
    CHECK_GT(10, 3);
}

TEST(c_consumer, STRING_CHECK) {
    const char* s = "tau-header-only";
    CHECK_STREQ(s, "tau-header-only");
    CHECK(strlen(s) == 15, "len(s) == 15");
}

TEST(c_consumer, FLOAT_EQ) {
    CHECK(0.1 + 0.2 > 0.3, "0.1 + 0.2 > 0.3");
}

MUON_MAIN()