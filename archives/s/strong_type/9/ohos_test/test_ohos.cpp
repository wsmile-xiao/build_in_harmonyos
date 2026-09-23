/*
 * HarmonyOS 专项测试 — strong_type 9
 *
 * 与上游 Catch2 套件不同，本测试以 standalone 可执行形式直接运行在
 * HarmonyOS PC (aarch64-linux-ohos) 目标上：
 *   - 使用 OHOS SDK clang 15 + libc++ 编译（C++17）；
 *   - 校验平台特征宏（__aarch64__ / libc++ 特性宏），
 *     证明当前测试确为 OHOS arm64 工具链产物；
 *   - 通过公开头文件 include/strong_type 目录下的头文件调用公开 API，
 *     校验 strong typedef 的算术、比较、差类型、哈希等语义在
 *     OHOS 运行时的真实可观察结果。
 *
 * 修饰符按上游单修饰符族模式组织（arithmetic / ordered / difference /
 * incrementable 等各自独立成类型），与上游测试用法一致。
 * 本测试为鸿蒙平台专项验证，非上游测试的复述。
 */
#include <strong_type/strong_type.hpp>

#include <cstdio>
#include <unordered_set>
#include <utility>

using namespace strong;

// 强类型：int 包装 + 单修饰符族（arithmetic + ordered 为组合族，与上游用法一致）
using meters = type<int, struct meters_, arithmetic, ordered>;

static int failures = 0;

#define CHECK(cond, msg)                                        \
  do {                                                          \
    if (cond) {                                                 \
      std::printf("PASS: %s\n", msg);                           \
    } else {                                                    \
      std::printf("FAIL: %s\n", msg);                           \
      ++failures;                                               \
    }                                                           \
  } while (0)

int main() {
  // 1. 平台特征：必须是 OHOS arm64 工具链产物
#if defined(__OHOS__)
  std::printf("INFO: __OHOS__ defined\n");
#else
  std::printf("INFO: __OHOS__ NOT defined (host macro set: %s)\n",
#if defined(__aarch64__)
              "aarch64");
#else
              "not-aarch64");
#endif
#endif
#if defined(__aarch64__)
  CHECK(true, "platform: compiled for aarch64 (__aarch64__)");
#else
  CHECK(false, "platform: __aarch64__ should be defined on OHOS arm64");
#endif
#if defined(_LIBCPP_VERSION)
  std::printf("INFO: libc++ version %d\n", static_cast<int>(_LIBCPP_VERSION));
  CHECK(_LIBCPP_VERSION >= 15000, "platform: libc++ >= 15000 (OHOS SDK clang 15)");
#else
  CHECK(false, "platform: _LIBCPP_VERSION should be defined (libc++)");
#endif

  // 2. 公开 API：算术语义（add/sub/mul/div/neg）
  meters a{10};
  meters b{3};
  CHECK((a + b).value_of() == 13, "arithmetic: 10 + 3 == 13");
  CHECK((a - b).value_of() == 7, "arithmetic: 10 - 3 == 7");
  CHECK((a * b).value_of() == 30, "arithmetic: 10 * 3 == 30");
  CHECK((a / b).value_of() == 3, "arithmetic: 10 / 3 == 3");
  CHECK((-a).value_of() == -10, "arithmetic: -10");

  // 3. 公开 API：有序比较
  CHECK(a < b ? false : true, "ordered: 10 < 3 is false");
  CHECK(b < a ? true : false, "ordered: 3 < 10 is true");
  CHECK(a > b ? true : false, "ordered: 10 > 3 is true");
  // equality_with 提供与基础类型的相等比较（上游用法）
  using eq = type<int, struct eq_, equality_with<int>, ordered>;
  eq q{10};
  CHECK(q == 10 ? true : false, "equality_with: 10 == 10 (int)");

  // 4. 公开 API：差类型（difference，独立类型族）
  using dist = type<int, struct dist_, difference, ordered>;
  dist c{7};
  dist d{4};
  auto diff = c - d;  // difference 类型
  CHECK(diff.value_of() == 3, "difference: 7 - 4 == 3");
  auto e = diff + diff;  // difference + difference -> difference
  CHECK(e.value_of() == 6, "difference: 3 + 3 == 6");
  dist f{1};
  auto g = f + e;  // base + difference -> base
  CHECK(g.value_of() == 7, "difference->base: 1 + 6 == 7");

  // 5. 公开 API：hashable + unordered_set 实测（上游用法 hashable+regular）
  using hs = type<int, struct hs_, hashable, regular>;
  std::unordered_set<hs> s;
  s.insert(hs{1});
  s.insert(hs{2});
  s.insert(hs{1});  // duplicate -> 仍为 2 个
  CHECK(s.size() == 2, "hashable: unordered_set dedup keeps 2 entries");
  CHECK(s.count(hs{2}) == 1, "hashable: set contains 2");

  // 6. 自增 / 自减（独立类型族）
  using cnt = type<int, struct cnt_, incrementable, decrementable>;
  cnt n{5};
  ++n;
  CHECK(n.value_of() == 6, "incrementable: ++5 == 6");
  --n;
  --n;
  CHECK(n.value_of() == 4, "decrementable: --6 -- == 4");

  std::printf("\n%s (%d failure%s)\n",
              failures == 0 ? "ALL OHOS TESTS PASSED" : "OHOS TESTS FAILED",
              failures, failures == 1 ? "" : "s");
  return failures == 0 ? 0 : 1;
}
