// Consumer test — quickcpplib 0.1.0.0-gh0.20231208
// 以库使用者身份使用 quickcpplib 的 boost 兼容单测 shim（这正是 outcome
// 等上游项目的真实消费方式），经 CMakeDeps + find_package 链接打包头，
// 以断言结果决定退出码。
#include "quickcpplib/boost/test/unit_test.hpp"

BOOST_AUTO_TEST_CASE(consumer_smoke, "shim compiles, asserts run, exit code reflects failures")
{
    int a = 2, b = 4;
    BOOST_CHECK_EQUAL(a + b, 6);
    BOOST_CHECK(a * b == 8);
    BOOST_CHECK_MESSAGE(a < b, "ordering check via BOOST_CHECK_MESSAGE");
}
