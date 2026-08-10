/* test_package/test.cpp — gtest 消费者测试 */
#include <gtest/gtest.h>

TEST(SmokeTest, Add) {
    EXPECT_EQ(1 + 1, 2);
}

TEST(SmokeTest, StringEq) {
    EXPECT_STREQ("hello", "hello");
}

int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}