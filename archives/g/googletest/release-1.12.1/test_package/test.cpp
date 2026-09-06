// googletest 消费者测试：链接打包的 libgtest*.a + libgmock*.a，真机实跑。
// 同时验证 gtest（TEST/EXPECT_*）与 gmock（MOCK_METHOD/EXPECT_CALL）在 OHOS 上可用。
#include <gtest/gtest.h>
#include <gmock/gmock.h>

using ::testing::_;
using ::testing::Return;

// gmock：模拟类 + 行为设置
class MockCalc {
public:
    MOCK_METHOD(int, add, (int, int));
};

// gtest：普通断言
TEST(GTestSmoke, Addition) {
    EXPECT_EQ(2 + 2, 4);
    EXPECT_GT(4, 2);
}

// gtest：字符串断言
TEST(GTestSmoke, StringEquals) {
    const char* s = "OHOS";
    EXPECT_STREQ(s, "OHOS");
}

// gmock：mock 调用断言
TEST(GMockSmoke, MockAddReturns) {
    MockCalc m;
    EXPECT_CALL(m, add(2, 3)).WillOnce(Return(5));
    EXPECT_EQ(m.add(2, 3), 5);
}

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
