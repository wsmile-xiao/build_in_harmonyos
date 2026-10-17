// Consumer / L1 test for libgeocoding 9.0.34 (Google libphonenumber offline geocoder).
//
// 全部用例都通过**已安装包的公开 C++ API** 真实执行离线地理编码：
//   phonenumbers/geocoding/phonenumber_offline_geocoder.h  （目标库公开头）
//   phonenumbers/phonenumberutil.h / phonenumber.pb.h      （同源解析 API，geocoder 必需）
//
// CHECK 6 是 HarmonyOS 专有回归用例（仅当 test_package 以
// -DLIBGEOCODING_TEST_OHOS=1 编译时执行）：在 OHOS 目标机上并发调用离线 geocoder，
// 覆盖本次适配修复的 absl::Mutex 加锁路径，并验证 geocoding 数据完全由编译期嵌入
// （不依赖任何外部数据文件 / 系统 locale）。
#include <cstdlib>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

#include "phonenumbers/geocoding/phonenumber_offline_geocoder.h"
#include "phonenumbers/phonenumber.pb.h"
#include "phonenumbers/phonenumberutil.h"
#include <unicode/locid.h>

using i18n::phonenumbers::PhoneNumber;
using i18n::phonenumbers::PhoneNumberOfflineGeocoder;
using i18n::phonenumbers::PhoneNumberUtil;

static int g_checks = 0;

static void check(bool ok, const std::string& name, const std::string& detail) {
  if (!ok) {
    std::cerr << "CHECK " << (g_checks + 1) << " " << name << " FAILED: "
              << detail << std::endl;
    std::exit(1);
  }
  ++g_checks;
  std::cout << "CHECK " << g_checks << " " << name << " OK: " << detail
            << std::endl;
}

static bool parse(const std::string& raw, const std::string& region,
                  PhoneNumber* number) {
  return PhoneNumberUtil::GetInstance()->Parse(
             raw, region, number) == PhoneNumberUtil::NO_PARSING_ERROR;
}

static std::string describe(const std::string& raw, const std::string& region,
                            const icu::Locale& locale) {
  PhoneNumber number;
  if (!parse(raw, region, &number)) {
    return "<parse-error>";
  }
  return PhoneNumberOfflineGeocoder().GetDescriptionForNumber(number, locale);
}

int main() {
  // CHECK 1: 公开解析 API 可用
  PhoneNumber us_number;
  check(parse("16502530000", "US", &us_number),
        "parse-us-number", "16502530000 parsed in region US");

  // CHECK 2: 号码有效性
  check(PhoneNumberUtil::GetInstance()->IsValidNumber(us_number),
        "validate-us-number", "16502530000 is a valid US number");

  // CHECK 3: 离线地理编码（上游样例的期望值）
  const std::string us_desc = describe("16502530000", "US", icu::Locale("en", "GB"));
  check(us_desc == "Mountain View, CA", "geocode-us-en", us_desc);

  // CHECK 4: 非拉丁语系本地化（ICU i18n 数据路径）
  const std::string cn_desc = describe("+861012345678", "CN", icu::Locale("zh", "CN"));
  check(cn_desc == "北京市", "geocode-cn-zh", cn_desc);

  // CHECK 5: 另一国家/地区的数据分支
  const std::string de_desc = describe("+4930901820", "DE", icu::Locale("de", "DE"));
  check(de_desc == "Berlin", "geocode-de-de", de_desc);

#ifdef LIBGEOCODING_TEST_OHOS
  std::cout << "DISCOVERED " << 6 << std::endl;
#else
  std::cout << "DISCOVERED " << 5 << std::endl;
#endif

#ifdef LIBGEOCODING_TEST_OHOS
  // CHECK 6 (HarmonyOS 专有): 并发调用离线 geocoder —— 覆盖本适配修复的
  // phonenumber_offline_geocoder.cc 中 absl::Mutex 加锁路径（~PhoneNumberOfflineGeocoder
  // 与 GetDescriptionForNumber 均持该锁）；同时验证结果只来自编译期嵌入的
  // geocoding 数据（OHOS 上不存在 /usr/share 数据文件与系统 locale 依赖）。
  const int kThreads = 8;
  std::vector<std::string> results(kThreads);
  std::vector<std::thread> threads;
  for (int i = 0; i < kThreads; ++i) {
    threads.emplace_back([i, &results]() {
      results[i] = describe("16502530000", "US", icu::Locale("en", "GB"));
    });
  }
  for (auto& t : threads) {
    t.join();
  }
  int consistent = 0;
  for (const auto& r : results) {
    if (r == "Mountain View, CA") {
      ++consistent;
    }
  }
  check(consistent == kThreads, "ohos-concurrent-geocoding-embedded-data",
        std::to_string(consistent) + "/" + std::to_string(kThreads) +
            " concurrent geocoding results consistent (embedded data, no locale files)");
#endif

  std::cout << "ALL " << g_checks << " CHECKS PASSED" << std::endl;
  return 0;
}
