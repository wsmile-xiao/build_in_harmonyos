#include <CppUTest/CommandLineTestRunner.h>
#include <CppUTest/TestHarness.h>
#include <CppUTestExt/MockSupport.h>
#include <cstring>

/* Real consumer assertions against the packaged CppUTest. */

TEST_GROUP(GroupBasics)
{
};

TEST(GroupBasics, integerAssertions)
{
    LONGS_EQUAL(4, 2 + 2);
    CHECK_TRUE(1 == 1);
    CHECK_FALSE(0 == 1);
    BYTES_EQUAL('a', 'a');
}

TEST(GroupBasics, stringAndCompare)
{
    STRCMP_EQUAL("weechat", "wee" "chat");
    DOUBLES_EQUAL(1.0, 1.0, 0.0001);
    POINTERS_EQUAL(NULL, NULL);
}

TEST(GroupBasics, failureMacrosExist)
{
    /* exercise the failure-signalling path in a controlled way */
    CHECK_TEXT(true, "this must not fail");
}

int main(int argc, char **argv)
{
    return CommandLineTestRunner::RunAllTests(argc, argv);
}
