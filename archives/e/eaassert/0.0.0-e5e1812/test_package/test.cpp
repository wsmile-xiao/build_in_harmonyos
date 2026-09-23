///////////////////////////////////////////////////////////////////////////////
// test_eaassert — Conan L1 消费者测试（HarmonyOS PC, aarch64-linux-ohos）
//
// 仅使用 EAAssert 安装后的公开头文件 <EAAssert/eaassert.h>、公开 API
// (EA::Assert::SetFailureCallback / GetFailureCallback) 与链接目标
// libEAAssert，验证第三方业务组件可编译、链接、调用并正常运行。
// 断言语义按 EA_ASSERT_ENABLED 编译模式双口径校验（与上游 TestEAAssert.cpp
// 的 TestCondition 同语义）：
//   - EA_ASSERT_ENABLED 定义时（Debug）：失败断言必须触发回调并携带
//     expr/filename/line/function/msg（含 va_list 格式化消息）；
//   - 未定义时（Release/NDEBUG）：断言宏为空操作，回调不得触发、表达式
//     副作用不得求值。
// 不使用 EAMain/EATest/EASTL 等测试框架，返回值为错误计数（0=通过）。
///////////////////////////////////////////////////////////////////////////////

#include <EAAssert/eaassert.h>
#include <cstdarg>
#include <cstdio>
#include <cstring>

static int gErrors = 0;

#define OH_CHECK(cond)                                                         \
    do {                                                                       \
        if (cond) std::printf("  [PASS] %s\n", #cond);                         \
        else { std::printf("  [FAIL] %s  (line %d)\n", #cond, __LINE__); ++gErrors; } \
    } while (0)

// 与上游 TestCondition 同语义：always=true 时条件必须成立（不随编译模式变化）；
// 否则按 EA_ASSERT_ENABLED 反转预期（断言关闭时条件应为假）。
static void TestCondition(bool condition, bool always)
{
    if (always)
    {
        OH_CHECK(condition);
        return;
    }
#if defined(EA_ASSERT_ENABLED)
    OH_CHECK(condition);
#else
    OH_CHECK(!condition);
#endif
}

static const char* gExpr = 0;
static const char* gFile = 0;
static int         gLine = 0;
static const char* gFunc = 0;
static const char* gMsg = 0;
static bool        gCalled = false;

static bool OhosAssertFailure(const char* expr, const char* filename, int line,
                              const char* function, const char* msg, va_list args)
{
    gCalled = true;
    gExpr = expr;
    gFile = filename;
    gLine = line;
    gFunc = function;
    if (msg)
    {
        static char buf[256];
        vsnprintf(buf, sizeof(buf), msg, args);
        gMsg = buf;
    }
    else
        gMsg = "";
    return false;
}

static bool TestExpressionWithSideEffect(bool* x)
{
    *x = !*x;
    return *x;
}

int main()
{
    const char* result = "FAIL";
    std::printf("EAAssert consumer test on %s\n", EA_PLATFORM_NAME);

    const char* testMsg = "The quick brown fox jumps over the lazy dog.";

    // ---- 1. 回调注册/获取（与编译模式无关）----
    EA::Assert::SetFailureCallback(&OhosAssertFailure);
    OH_CHECK(EA::Assert::GetFailureCallback() == &OhosAssertFailure);

    // ---- 2. 失败断言触发语义（双模式）----
    const char* mainName = "main";
    gCalled = false;
    EA_ASSERT(3 == 4);
    TestCondition(gCalled, false);   // 启用→必须触发；关闭→不得触发
#if defined(EA_ASSERT_ENABLED)
    OH_CHECK(gExpr && 0 == std::strcmp(gExpr, "3 == 4"));
    OH_CHECK(gFile && 0 != std::strstr(gFile, "test.cpp"));
    OH_CHECK(gLine != 0);
    OH_CHECK(gFunc && 0 != std::strstr(gFunc, mainName));
#endif

    // ---- 3. 带消息/格式化断言（仅启用模式下校验消息内容）----
    gCalled = false;
    gMsg = 0;
    EA_ASSERT_M(3 == 4, testMsg);
    TestCondition(gCalled, false);
#if defined(EA_ASSERT_ENABLED)
    OH_CHECK(gMsg && 0 == std::strcmp(gMsg, testMsg));
#endif

    gCalled = false;
    gMsg = 0;
    EA_ASSERT_MSG(3 == 4, testMsg);
    TestCondition(gCalled, false);
#if defined(EA_ASSERT_ENABLED)
    OH_CHECK(gMsg && 0 == std::strcmp(gMsg, testMsg));
#endif

    gCalled = false;
    gMsg = 0;
    EA_ASSERT_FORMATTED(8 == 2, ("The quick brown fox jumps over the %s dog.", "lazy"));
    TestCondition(gCalled, false);
#if defined(EA_ASSERT_ENABLED)
    OH_CHECK(gMsg && 0 == std::strcmp(gMsg, "The quick brown fox jumps over the lazy dog."));
#endif

    // ---- 4. EA_FAIL 无条件触发（双模式）----
    gCalled = false;
    EA_FAIL();
    TestCondition(gCalled, false);
#if defined(EA_ASSERT_ENABLED)
    OH_CHECK(gExpr && 0 == std::strcmp(gExpr, "EA_FAIL"));
#endif

    // ---- 5. 表达式副作用按 EA_ASSERT_ENABLED 求值 ----
    bool expressionCalled = false;
    EA_ASSERT(TestExpressionWithSideEffect(&expressionCalled));
#if defined(EA_ASSERT_ENABLED)
    OH_CHECK(expressionCalled);
#else
    OH_CHECK(!expressionCalled);
#endif

    // ---- 6. EA_PANIC 真值不崩溃 + 编译期断言 ----
    EA_PANIC(4 == 4);
    EA_PANIC_MSG(4 == 4, testMsg);
    EA_PANIC_FORMATTED(8 == 8, ("%s", testMsg));
    EA_COMPILETIME_ASSERT(sizeof(int) >= 4);

    if (gErrors == 0) result = "PASS";
    std::printf("EAAssert consumer test result: %s (errors=%d)\n", result, gErrors);
    return gErrors;
}