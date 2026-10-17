// gmock 实质 API 测试：MockFoo + EXPECT_CALL + matcher（R34）
#include <gmock/gmock.h>
#include <gtest/gtest.h>

using ::testing::Return;
using ::testing::_;

class MockFoo {
public:
    MOCK_METHOD(int, bar, (int x));
};

TEST(GmockSmoke, ExpectCall) {
    MockFoo foo;
    EXPECT_CALL(foo, bar(42)).WillOnce(Return(7));
    EXPECT_EQ(7, foo.bar(42));
}

int main(int argc, char** argv) {
    ::testing::InitGoogleMock(&argc, argv);
    return RUN_ALL_TESTS();
}
