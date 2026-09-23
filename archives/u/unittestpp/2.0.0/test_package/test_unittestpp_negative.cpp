// test_package/test_unittestpp_negative.cpp — 反向对照（预期失败，rc=2）
//
// 目的：证明框架不会把失败静默吞掉——
//   1. check_failure_probe：CHECK_EQUAL 失败 → 必须报告 1 个 failure；
//   2. signal_probe：raise(SIGSEGV) 触发信号 → 由 Posix SignalTranslator
//      （sigsetjmp/sigaction/siglongjmp）翻译为测试失败而非进程崩溃 ——
//      OHOS 平台特有的信号路径验证。
//      注：用 raise() 而非上游 TestTest.cpp 的空指针函数调用；实测该设备上
//      "执行空指针函数调用"的硬件指令中止会让进程挂起（raise/空指针数据
//      访问/__builtin_trap 均正常翻译），deterministic 起见用 raise()。
// 预期输出：FAILURE: 2 out of 3 tests failed (2 failures). 以及
//          "Unhandled exception: test crashed"；退出码 = 2（failure 数）。
#include "UnitTest++/UnitTestPP.h"

#include <csignal>

TEST(passing_probe)
{
   CHECK(true);
}

TEST(check_failure_probe)
{
   CHECK_EQUAL(42, 41);   // 预期失败
}

TEST(signal_probe)
{
   raise(SIGSEGV);        // 信号 → 翻译为测试失败
   CHECK(false);          // 不应到达
}

int main()
{
   return UnitTest::RunAllTests();
}
