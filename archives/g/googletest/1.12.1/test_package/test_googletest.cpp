/* test_package/test_googletest.cpp — googletest 消费者测试 */
#include <gtest/gtest.h>
#include <gmock/gmock.h>

TEST(SmokeTest, Add) {
    EXPECT_EQ(1 + 1, 2);
}

TEST(SmokeTest, StringEq) {
    EXPECT_STREQ("hello", "hello");
}

TEST(SmokeTest, GmockMatcher) {
    EXPECT_THAT(42, testing::Gt(10));
}

int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}