/* test_unity.c — Unity 2.7.0 冒烟测试：真实链接被测库核心 src/unity.c，
 * 跑 UnityBegin/RUN_TEST/UNITY_END 完整生命周期。 */
#include <stdio.h>

/* 输出字符钩子：须在 include unity.h 之前定义（函数式宏，不进命令行）。
 * 上游契约（unity_internals.h）：extern void <HEADER_DECLARATION>;
 * 故签名必须为 void f(int)；声明由头文件生成，勿再手写。 */
#define UNITY_OUTPUT_CHAR(a) putcharSpy(a)
#define UNITY_OUTPUT_CHAR_HEADER_DECLARATION putcharSpy(int)

#include <unity.h>

void putcharSpy(int c) { (void)c; }

/* Unity 约定：每个测试程序必须提供 setUp/tearDown */
void setUp(void) {}
void tearDown(void) {}

static void testSmokeAssertion(void)
{
    int a = 42;
    TEST_ASSERT_EQUAL_INT(42, a);
    TEST_ASSERT_EQUAL_STRING("unity", "unity");
}

static void testSmokeFloat(void)
{
    float f = 1.5f;
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 1.5f, f);
}

int main(void)
{
    UnityBegin("test_unity");
    RUN_TEST(testSmokeAssertion);
    RUN_TEST(testSmokeFloat);
    return UNITY_END();
}
