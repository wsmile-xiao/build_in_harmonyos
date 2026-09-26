// Consumer tests for unittest-cpp (UnitTest++ 2.0.0) on HarmonyOS PC.
// 以库使用者身份真实编译+链接 UnitTest++ 静态库并调用公开 API：
//   A1  RunAllTests 全局注册路径（本 TU 两个 TEST 宏用例）→ 0 失败；
//   A2  SignalTranslator 反向验证：故意解引用空指针的用例必须被计为
//       "crashed" 失败（sigaction+siglongjmp 在 OHOS/musl 下真实生效；
//       翻译失效时进程会直接 SIGSEGV 死掉，走不到这里的断言）；
//   A3  MemoryOutStream 公开 API 行为断言；
//   A4  TestResults 失败计数语义断言（CHECK(false) 计 1 失败）。
// 任一断言失败 → exit 非 0 → ctest FAIL。

#include <UnitTest++/UnitTest++.h>
#include <UnitTest++/CurrentTest.h>
#include <cstring>
#include <cstdio>

using namespace UnitTest;

TEST(ConsumerRunnerPathWorks)
{
    CHECK(1 == 1);
    CHECK_EQUAL(4, 2 + 2);
    CHECK(std::strcmp("unittest-cpp", "unittest-cpp") == 0);
}

TEST(TimeConstraintApiPresent)
{
    // 真实调用库公共符号：GetTimeInMs 由 Posix 平台层实现
    UNITTEST_TIME_CONSTRAINT(100);
    CHECK(1 == 1);
}

namespace {
    struct ScopedResults
    {
        explicit ScopedResults(TestResults& r)
            : m_prev(CurrentTest::Results())
        {
            CurrentTest::Results() = &r;
        }
        ~ScopedResults() { CurrentTest::Results() = m_prev; }
        TestResults* m_prev;
    };

    class CrashingConsumerTest : public Test
    {
    public:
        CrashingConsumerTest() : Test("deliberate-crash", "ProbeSuite") {}
        virtual void RunImpl() const override
        {
            volatile int* p = nullptr;
            *p = 42;                 // SIGSEGV → SignalTranslator 翻译
            CHECK(*p == 42);         // 不可达
        }
    };
}

int main()
{
    int failures = 0;

    // A1：全局注册表 + RunAllTests（本 TU 的两个 TEST 宏用例）
    // 临时摘除全局链表中 crash 探针不受影响：CrashingConsumerTest 非宏注册。
    int rc = UnitTest::RunAllTests();
    if (rc == 0) { std::printf("PASS: A1 RunAllTests==0\n"); }
    else { std::printf("FAIL: A1 RunAllTests=%d\n", rc); ++failures; }

    // A2：故意崩溃用例必须被翻译为 1 条失败（含 crash 语义），进程存活至此即证据
    {
        TestResults results;
        {
            ScopedResults scoped(results);
            CrashingConsumerTest().Run();
        }
        if (results.GetFailureCount() == 1)
            std::printf("PASS: A2 crash translated to exactly 1 failure\n");
        else {
            std::printf("FAIL: A2 failureCount=%d (expected 1)\n", results.GetFailureCount());
            ++failures;
        }
    }

    // A3：MemoryOutStream 公开 API
    {
        MemoryOutStream s;
        s << 42 << "-" << "mc";
        if (std::strcmp(s.GetText(), "42-mc") == 0)
            std::printf("PASS: A3 MemoryOutStream format\n");
        else {
            std::printf("FAIL: A3 got \"%s\"\n", s.GetText());
            ++failures;
        }
    }

    // A4：CHECK(false) 经 TestResults 计 1 失败
    {
        TestResults results;
        {
            ScopedResults scoped(results);
            results.OnTestFailure(TestDetails("x", "s", "f.cpp", 1), "manual");
        }
        if (results.GetFailureCount() == 1 && results.GetTotalTestCount() == 0)
            std::printf("PASS: A4 TestResults failure semantics\n");
        else {
            std::printf("FAIL: A4 failures=%d tests=%d\n",
                        results.GetFailureCount(), results.GetTotalTestCount());
            ++failures;
        }
    }

    std::printf("SUMMARY: %s (%d assertion failures)\n",
                failures == 0 ? "ALL PASS" : "FAILED", failures);
    return failures == 0 ? 0 : 1;
}
