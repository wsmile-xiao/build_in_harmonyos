// test.cpp — kweathercore 26.04.0 消费者测试 (Conan L1)
// 实质调用 kweathercore API：LocationQueryResult 值对象（构造/访问器），
// 版本宏校验。任一声明失败返回非 0（链接/头文件缺失也会在编译期暴露）。
// API 依 kweathercore-26.04.0/src/locationqueryresult.h 真实签名。
#include <KWeatherCore/locationqueryresult.h>
#include <kweathercore_version.h>

#include <QtCore/QString>
#include <cstdio>
#include <optional>

namespace {

int g_checks = 0;

bool check(bool condition, const char* what)
{
  ++g_checks;
  if (!condition)
    std::fprintf(stderr, "FAIL: %s\n", what);
  return condition;
}

} // namespace

int main()
{
  bool ok = true;

  // 1. 版本宏：version.h 由包提供。
#ifdef KWEATHERCORE_VERSION_STRING
  ok &= check(true, "KWEATHERCORE_VERSION_STRING defined");
#else
  ok = false;
  std::fprintf(stderr, "FAIL: KWEATHERCORE_VERSION_STRING not defined\n");
#endif

  // 2. KWeatherCore::LocationQueryResult —— 核心值对象
  //    （libKWeatherCore 符号依赖）。C++20 下 u"" 为 char8_t*，
  //    QString 无该构造，用 fromUtf8 显式构造。
  KWeatherCore::LocationQueryResult loc(55.75, 37.62,
                                        QString::fromUtf8("Moscow"),
                                        QString::fromUtf8("Moscow"),
                                        QString::fromUtf8("RU"),
                                        QString::fromUtf8("524901"));
  ok &= check(loc.latitude() == 55.75, "LocationQueryResult::latitude");
  ok &= check(loc.name() == QString::fromUtf8("Moscow"), "LocationQueryResult::name");
  ok &= check(loc.countryCode() == QString::fromUtf8("RU"), "LocationQueryResult::countryCode");

  if (!ok)
  {
    std::fprintf(stderr, "kweathercore test: %d checks, FAILURES present\n", g_checks);
    return 1;
  }

  std::printf("kweathercore 26.04.0: all %d checks passed\n", g_checks);
  return 0;
}
