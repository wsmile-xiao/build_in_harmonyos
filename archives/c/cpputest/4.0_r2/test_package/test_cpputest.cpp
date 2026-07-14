// test_cpputest.cpp — L1 smoke test for cpputest framework
// 用 cpputest 编写一个简单的单元测试, 验证框架可用
#include <CppUTest/CommandLineTestRunner.h>
#include <CppUTest/TestHarness.h>

// 简单的数学运算 (被测代码)
static int add(int a, int b) {
    return a + b;
}

static int multiply(int a, int b) {
    return a * b;
}

// Test 1: 加法测试
TEST_GROUP(MathTests)
{
    void setup() {}
    void teardown() {}
};

TEST(MathTests, AddPositiveNumbers) {
    CHECK_EQUAL(5, add(2, 3));
}

TEST(MathTests, AddZero) {
    CHECK_EQUAL(7, add(7, 0));
}

TEST(MathTests, AddNegative) {
    CHECK_EQUAL(-1, add(2, -3));
}

// Test 2: 乘法测试
TEST(MathTests, MultiplyPositive) {
    CHECK_EQUAL(6, multiply(2, 3));
}

TEST(MathTests, MultiplyByZero) {
    CHECK_EQUAL(0, multiply(42, 0));
}

// Test 3: 字符串比较
TEST_GROUP(StringTests)
{
    void setup() {}
    void teardown() {}
};

TEST(StringTests, StringComparison) {
    STRCMP_EQUAL("hello", "hello");
}

int main(int argc, char** argv) {
    return CommandLineTestRunner::RunAllTests(argc, argv);
}
