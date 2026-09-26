#ifndef JAULA_TEST_CHECK_H
#define JAULA_TEST_CHECK_H
// 三个消费者程序共用的断言器：断言失败即计一次失败，main 以非零退出码结束，
// 由 conan 的 test() 判定成败（不靠打印人读）。
#include <iostream>

static int g_checks = 0;
static int g_failures = 0;

static void check(bool ok, const char *what)
{
  ++g_checks;
  if (!ok)
  {
    ++g_failures;
    std::cerr << "FAIL: " << what << std::endl;
  }
}

static int finish(const char *program)
{
  std::cout << program << ": " << (g_checks - g_failures) << "/" << g_checks
            << " assertions passed" << std::endl;
  return g_failures == 0 ? 0 : 1;
}
#endif
