// HarmonyOS 专项测试: tl-expected 1.1.0
// 覆盖 std::expected 在实际消费入口上的使用: 值/错误分支、and_then/map 链式调用、
// 常量表达式路径、HarmonyOS 平台宏与版本标识。
#include <tl/expected.hpp>
#include <cstdio>
#include <cstring>
#include <string>

#if defined(__OHOS__) || defined(__OHOS_FAMILY__) || defined(HARMONYOS)
#define TL_EXPECTED_OHOS_OK 1
#elif defined(__linux__) && defined(__aarch64__)
#warning "Linux aarch64 build: running on HarmonyOS-compatible aarch64 kernel"
#define TL_EXPECTED_OHOS_OK 1
#else
#define TL_EXPECTED_OHOS_OK 0
#endif

using tl::expected;
using tl::unexpected;

static int g_checks = 0;
static int g_ok = 0;

#define CHECK(cond)                                              \
  do {                                                           \
    ++g_checks;                                                  \
    if (!(cond)) {                                               \
      std::printf("FAIL [%s:%d]: %s\n", __FILE__, __LINE__, #cond); \
      return 1;                                                  \
    }                                                            \
    ++g_ok;                                                      \
  } while (0)

// HarmonyOS errno 风格错误码消费
static int ohos_errno_style() {
  expected<int, int> ok_v = 42;
  CHECK(ok_v.has_value());
  CHECK(ok_v.value() == 42);

  expected<int, int> err_v = unexpected<int>(-1);
  CHECK(!err_v.has_value());
  CHECK(err_v.error() == -1);

  // value_or 兜底路径（应用层常用）
  CHECK(err_v.value_or(7) == 7);
  CHECK(ok_v.value_or(7) == 42);
  return 0;
}

// 链式调用: and_then / map（消费入口常用模式）
static int chaining() {
  expected<int, std::string> a = 5;
  auto r = a.and_then([](int v) -> expected<int, std::string> {
    if (v < 0) return unexpected<std::string>("negative");
    return v * 2;
  }).map([](int v) { return v + 1; });
  CHECK(r.has_value());
  CHECK(r.value() == 11);
  return 0;
}

// 常量表达式路径（make_unexpected 在 1.1.0 中非 constexpr，仅在运行时校验）
static int constexpr_path() {
  constexpr auto e = expected<int, int>(3);
  static_assert(e.has_value(), "constexpr expected has value");
  using eii = expected<int, int>;
  auto u = tl::make_unexpected(9);
  CHECK(!eii(u).has_value());
  CHECK(eii(u).error() == 9);
  CHECK(e.value() == 3);
  return 0;
}

// 版本标识与平台宏
static int version_and_platform() {
  CHECK(TL_EXPECTED_VERSION_MAJOR == 1);
  CHECK(TL_EXPECTED_VERSION_MINOR == 1);
  CHECK(TL_EXPECTED_VERSION_PATCH == 0);
#if TL_EXPECTED_OHOS_OK
  std::printf("platform: HarmonyOS/aarch64 detected\n");
  ++g_ok;
#else
  std::printf("platform: non-OHOS build (test skipped macros)\n");
#endif
  return 0;
}

static int value_types_and_nested() {
  expected<std::string, int> s = std::string("ohos");
  CHECK(s.value() == "ohos");
  expected<expected<int, int>, int> nested = expected<int, int>(1);
  CHECK(nested.has_value());
  CHECK(nested.value().value() == 1);
  return 0;
}

int main() {
  std::printf("== tl-expected 1.1.0 HarmonyOS 专项测试 ==\n");
  std::printf("arch: %s, OHOS macro: %d\n",
#if defined(__aarch64__)
              "aarch64",
#else
              "unknown",
#endif
              TL_EXPECTED_OHOS_OK);
  int rc = 0;
  rc |= ohos_errno_style();
  rc |= chaining();
  rc |= constexpr_path();
  rc |= version_and_platform();
  rc |= value_types_and_nested();
  std::printf("checks=%d ok=%d result=%s\n", g_checks, g_ok,
              rc == 0 ? "PASS" : "FAIL");
  return rc;
}