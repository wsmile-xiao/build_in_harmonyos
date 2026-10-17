// fuzzrun 编译期最小 shim:中性化 FuzzTest 框架(google/fuzztest)的注册宏与域构造。
//
// 用途: libwebp 1.6.0 上游 12 个 tests/fuzzer/*_fuzzer.cc 均为 FUZZ_TEST(...) +
//       .WithDomains(...) 体系,需要 fuzztest 运行时(依赖 abseil)方可运行。
//       本 shim 在【编译期】把 FUZZ_TEST 注册与域对象变成空壳,使上游被测函数
//       (Test 函数本身)可在零改动前提下被外部 driver 直接调用执行。
//
// 注意: 本 shim 只保证编译通过;域对象永不参与运行期计算(域生成由 driver 的
//       显式种子/参数替代),运行期语义 = 直接执行上游被测函数。
#ifndef FUZZRUN_FUZZTEST_SHIM_H_
#define FUZZRUN_FUZZTEST_SHIM_H_

#include <cstddef>
#include <initializer_list>
#include <string>
#include <string_view>
#include <tuple>
#include <utility>
#include <vector>

namespace fuzztest {

// 通用域对象空壳:构造函数吸收一切实参,链式 .WithMaxSize/.WithMinSize 返回自身。
struct Domain {
  template <typename... Args>
  explicit Domain(Args&&...) {}
  Domain WithMaxSize(size_t) const { return *this; }
  Domain WithMinSize(size_t) const { return *this; }
};

// FUZZ_TEST 注册器空壳:.WithDomains(...)/.WithSeeds(...) 吸收一切实参。
struct Registrar {
  template <typename... Args>
  Registrar WithDomains(Args&&...) const { return *this; }
  template <typename... Args>
  Registrar WithSeeds(Args&&...) const { return *this; }
};

inline Domain String() { return Domain(); }
template <typename T> Domain Arbitrary() { return Domain(); }
template <typename T> Domain InRange(T, T) { return Domain(); }
template <typename T> Domain ElementOf(std::initializer_list<T>) {
  return Domain();
}
template <typename... D> Domain Map(D&&...) { return Domain(); }
template <typename... D> Domain FlatMap(D&&...) { return Domain(); }
template <typename... D> Domain PairOf(D&&...) { return Domain(); }
template <typename... D> Domain OptionalOf(D&&...) { return Domain(); }
template <typename... D> Domain Just(D&&...) { return Domain(); }
// StructOf/VectorOf 支持显式模板实参(如 StructOf<FrameConfig>(...)),
// T 不可推导时回退 void。
template <typename T = void, typename... D> Domain StructOf(D&&...) {
  return Domain();
}
template <typename T = void, typename... D> Domain VectorOf(D&&...) {
  return Domain();
}

// fuzz_utils.cc 的调用点要求返回 std::vector<std::tuple<std::string>>。
inline std::vector<std::tuple<std::string>> ReadFilesFromDirectory(
    std::string_view) {
  return std::vector<std::tuple<std::string>>();
}

}  // namespace fuzztest

// FUZZ_TEST(Suite, Func).WithDomains(...) → 静态空壳注册(匿名命名空间内,每 TU 唯一)。
#define FUZZ_TEST(SUITE, FUNC)                                          \
  static ::fuzztest::Registrar FuzzTestRegistration_##SUITE##_##FUNC    \
      [[maybe_unused]] = ::fuzztest::Registrar()

#endif  // FUZZRUN_FUZZTEST_SHIM_H_
