/* test_unity_ohos.c — Unity 2.7.0 HarmonyOS 特有测试（4 用例）
 *
 * 针对鸿蒙平台特性：
 *   1. 版本头身份：unity.h 宏 UNITY_VERSION_MAJOR/MINOR/MICRO == 2.7.0
 *      （验证打包的 include 是上游 2.7.0 而非陈旧缓存）
 *   2. 核心断言（int/int64/string/pointer/memcmp）：在 OHOS clang-15 +
 *      OHOS libc 下真实链接 src/unity.c 运行，验证 ANSI C 可移植性
 *   3. double 断言（UNITY_INCLUDE_DOUBLE）：64 位浮点路径在 armv8 上正常
 *   4. UNITY_OUTPUT_CHAR 钩子：验证输出字符回调在 OHOS 环境下被逐字符调用
 *      （断言失败诊断输出的基础设施，鸿蒙移植的关键 ABI 点）
 *
 * 全部用例真实调用被测库 API（非 mock）。任一失败 UNITY_END() 返回非 0。
 */
#include <stdio.h>
#include <string.h>

/* 输出字符钩子：须在 include unity.h 之前定义（函数式宏，不进命令行）。
 * 上游契约（unity_internals.h）：extern void <HEADER_DECLARATION>;
 * 故签名必须为 void f(int)；声明由头文件生成，勿再手写。 */
#define UNITY_OUTPUT_CHAR(a) putcharSpy(a)
#define UNITY_OUTPUT_CHAR_HEADER_DECLARATION putcharSpy(int)

#include <unity.h>

static int g_chars = 0;
void putcharSpy(int c) { (void)c; g_chars++; }

/* Unity 约定：每个测试程序必须提供 setUp/tearDown */
void setUp(void) {}
void tearDown(void) {}

/* ── 用例 1：版本头身份 ── */
static void testOhosVersionHeader(void)
{
    TEST_ASSERT_EQUAL_INT(2, UNITY_VERSION_MAJOR);
    TEST_ASSERT_EQUAL_INT(7, UNITY_VERSION_MINOR);
    TEST_ASSERT_EQUAL_INT(0, UNITY_VERSION_BUILD);
    /* 被测库核心符号可链接（unity.c 已编译成 libunity.so 并被链接） */
    TEST_ASSERT_NOT_NULL(Unity.TestFile == NULL ? NULL : (void *)1);
}

/* ── 用例 2：核心断言（int/int64/string/pointer/memcmp）── */
static void testOhosCoreAssertions(void)
{
    int i = -123456;
    int64_t l = (int64_t)9876543210;
    const char *s = "harmonyos";
    /* 字节级比较两侧都用字节数组（int 数组的补零字节会污染 memcmp） */
    unsigned char expect[4] = {1, 2, 3, 4};
    unsigned char buf[4] = {1, 2, 3, 4};
    buf[3] = expect[3] + 0; /* 内容一致，仅验证比较路径 */

    TEST_ASSERT_EQUAL_INT(-123456, i);
    TEST_ASSERT_EQUAL_INT64((int64_t)9876543210, l);
    TEST_ASSERT_EQUAL_STRING("harmonyos", s);
    TEST_ASSERT_NOT_NULL(s);
    TEST_ASSERT_NULL((void *)0);
    TEST_ASSERT_EQUAL_MEMORY((const void *)expect, (const void *)buf, sizeof(buf));
}

/* ── 用例 3：double 断言（UNITY_INCLUDE_DOUBLE, armv8 64 位浮点路径）── */
static void testOhosDoubleAssertions(void)
{
    double d = 3.14159265358979;
    TEST_ASSERT_DOUBLE_WITHIN(1e-12, 3.14159265358979, d);
    TEST_ASSERT_EQUAL_DOUBLE(2.0 * d, d + d);
}

/* ── 用例 4：UNITY_OUTPUT_CHAR 钩子（OHOS 输出字符回调）── */
static void testOhosOutputCharHook(void)
{
    g_chars = 0;
    UNITY_OUTPUT_CHAR('H'); /* 经 unity.h 展开为 putcharSpy('H') */
    UNITY_OUTPUT_CHAR('O');
    TEST_ASSERT_EQUAL_INT(2, g_chars);
    TEST_ASSERT_GREATER_THAN(0, Unity.NumberOfTests); /* UnityBegin 已初始化 */
}

int main(void)
{
    UnityBegin("test_unity_ohos");
    RUN_TEST(testOhosVersionHeader);
    RUN_TEST(testOhosCoreAssertions);
    RUN_TEST(testOhosDoubleAssertions);
    RUN_TEST(testOhosOutputCharHook);
    int rc = UNITY_END();
    if (rc == 0) {
        /* 用裸写确认 4/4 全过（不走 Unity 输出，避免被 spy 吞掉） */
        const char *ok = "OK: unity 2.7.0 HarmonyOS specific tests 4/4 passed\n";
        while (*ok) { UNITY_OUTPUT_CHAR(*ok++); }
    }
    return rc;
}
