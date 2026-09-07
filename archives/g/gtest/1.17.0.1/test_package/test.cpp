/* test_package/test.cpp — GTest and GMock consumer test */
#include <gmock/gmock.h>

TEST(SmokeTest, Add) {
    EXPECT_EQ(1 + 1, 2);
}

TEST(SmokeTest, GMockMatcher) {
    EXPECT_THAT("openharmony", ::testing::HasSubstr("harmony"));
}
