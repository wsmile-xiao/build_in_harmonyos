// test_package/test_unittestpp.cpp — unittestpp 2.0.0 消费者正向用例（9 个）
//
// 只使用打包的公共头文件（UnitTest++/UnitTestPP.h）与静态库 libUnitTest++.a。
// RunAllTests() 返回失败数：全过 = 0（进程退出码 0），并发输出
// "Success: 9 tests passed."。
#include "UnitTest++/UnitTestPP.h"

#include <stdexcept>
#include <string>

namespace {

int add(int a, int b)
{
   return a + b;
}

struct ConsumerFixture
{
   ConsumerFixture() : counter(41) {}
   int counter;
};

}

TEST(BasicChecks)
{
   CHECK(true);
   CHECK(!false);
   CHECK_EQUAL(42, add(40, 2));
   CHECK(3 < 4);
}

TEST(FloatingPointChecks)
{
   CHECK_CLOSE(3.14159, 3.1416, 0.001);
   CHECK_CLOSE(1.0, 1.0000001, 1e-5);
}

TEST(StringChecks)
{
   std::string const value("unittestpp-on-ohos");
   CHECK_EQUAL(std::string("unittestpp-on-ohos"), value);
   CHECK(value.find("ohos") != std::string::npos);
}

TEST(ArrayChecks)
{
   int const expected[] = { 1, 2, 3, 4 };
   int const actual[]   = { 1, 2, 3, 4 };
   CHECK_ARRAY_EQUAL(expected, actual, 4);

   double const expectedClose[] = { 1.0, 2.5 };
   double const actualClose[]   = { 1.0000001, 2.5000001 };
   CHECK_ARRAY_CLOSE(expectedClose, actualClose, 2, 1e-5);
}

TEST(ExceptionChecks)
{
   CHECK_THROW(throw std::runtime_error("expected"),
               std::runtime_error);
}

TEST_FIXTURE(ConsumerFixture, FixtureLifecycle)
{
   CHECK_EQUAL(41, counter);
   counter = add(counter, 1);
   REQUIRE CHECK_EQUAL(42, counter);
   CHECK(counter == 42);
}

SUITE(OhosConsumerSuite)
{
   TEST(SuiteScopedCase)
   {
      CHECK_EQUAL(2, add(1, 1));
   }
}

// OHOS 平台层（Posix）实跑：gettimeofday/usleep 计时路径
TEST(OhosPosixTimerAndSleep)
{
   UnitTest::Timer timer;
   timer.Start();
   UnitTest::TimeHelpers::SleepMs(10);
   double const elapsedMs = timer.GetTimeInMs();
   CHECK(elapsedMs >= 9.0);
   CHECK(elapsedMs < 5000.0);
}

// 时间约束机制（需 TEST_FIXTURE 作用域内的 m_details）
TEST_FIXTURE(ConsumerFixture, TimeConstraintIsHonored)
{
   UNITTEST_TIME_CONSTRAINT(1000);
   UnitTest::TimeHelpers::SleepMs(2);
   CHECK(true);
}

int main()
{
   return UnitTest::RunAllTests();
}
