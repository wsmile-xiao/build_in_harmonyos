#include <atf-c.h>
#include <string.h>

ATF_TC(pass_test);
ATF_TC_HEAD(pass_test, tc)
{
    atf_tc_set_md_var(tc, "descr", "A test case that always passes");
}
ATF_TC_BODY(pass_test, tc)
{
    ATF_REQUIRE_EQ(1, 1);
    ATF_CHECK_STREQ("hello", "hello");
}

ATF_TC(str_compare_test);
ATF_TC_HEAD(str_compare_test, tc)
{
    atf_tc_set_md_var(tc, "descr", "Test string comparison functions");
}
ATF_TC_BODY(str_compare_test, tc)
{
    const char *s = "atf-test";
    ATF_REQUIRE(strlen(s) == 8);
    ATF_CHECK(strcmp(s, "atf-test") == 0);
}

ATF_TC(math_test);
ATF_TC_HEAD(math_test, tc)
{
    atf_tc_set_md_var(tc, "descr", "Test basic math operations");
}
ATF_TC_BODY(math_test, tc)
{
    int a = 10, b = 20;
    ATF_REQUIRE_EQ(30, a + b);
    ATF_REQUIRE(a < b);
}

ATF_TP_ADD_TCS(tp)
{
    ATF_TP_ADD_TC(tp, pass_test);
    ATF_TP_ADD_TC(tp, str_compare_test);
    ATF_TP_ADD_TC(tp, math_test);
    return atf_no_error();
}
