/* test_package/test.cpp — GTest and GMock consumer test */
#include <gmock/gmock.h>
#include <gtest/gtest.h>

TEST(SmokeTest, Add) {
    EXPECT_EQ(1 + 1, 2);
}

TEST(SmokeTest, GMockMatcher) {
    EXPECT_THAT("openharmony", ::testing::HasSubstr("harmony"));
}

TEST(SmokeTest, GMockMockObject) {
    // 验证 GTest::gmock 组件（mock 对象 + matcher）实际可用
    class MockFoo {
    public:
        MOCK_METHOD(int, GetValue, (), (const));
    };
    MockFoo foo;
    EXPECT_CALL(foo, GetValue()).WillOnce(::testing::Return(42));
    EXPECT_EQ(foo.GetValue(), 42);
}
