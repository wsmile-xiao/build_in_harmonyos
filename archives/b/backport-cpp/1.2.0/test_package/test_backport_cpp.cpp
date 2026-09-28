// test_backport_cpp.cpp — backport-cpp 1.2.0 消费者测试（鸿蒙特有测试行）
//
// 一个 TU 依次包含全部 16 个公开头（等价于上游 AddSelfContainmentTest 的
// 消费端形态），再对回移 API 逐条断言；CHECK 宏自计数，退出码非 0 即失败。
#include <bpstd/any.hpp>
#include <bpstd/chrono.hpp>
#include <bpstd/complex.hpp>
#include <bpstd/cstddef.hpp>
#include <bpstd/exception.hpp>
#include <bpstd/functional.hpp>
#include <bpstd/iterator.hpp>
#include <bpstd/memory.hpp>
#include <bpstd/optional.hpp>
#include <bpstd/span.hpp>
#include <bpstd/string.hpp>
#include <bpstd/string_view.hpp>
#include <bpstd/tuple.hpp>
#include <bpstd/type_traits.hpp>
#include <bpstd/utility.hpp>
#include <bpstd/variant.hpp>

#include <cstdio>
#include <string>
#include <vector>

static int g_checks = 0;
static int g_failed = 0;

#define CHECK(cond)                                     \
  do {                                                  \
    ++g_checks;                                         \
    if (!(cond)) {                                      \
      ++g_failed;                                       \
      std::printf("FAIL[%d]: %s\n", g_checks, #cond);   \
    }                                                   \
  } while (false)

int main() {
  using bpstd::optional;
  using bpstd::string_view;
  using bpstd::variant;

  // ── optional（回移 C++17 std::optional）──
  optional<int> empty;
  CHECK(!empty.has_value());
  optional<int> o(42);
  CHECK(o.has_value());
  CHECK(*o == 42);
  CHECK(o.value() == 42);
  o.emplace(7);
  CHECK(o.value() == 7);

  // ── variant（回移 C++17 std::variant）──
  variant<int, double> v(3);
  CHECK(v.index() == 0u);
  CHECK(bpstd::get<int>(v) == 3);
  v = 2.5;
  CHECK(v.index() == 1u);
  CHECK(bpstd::get<double>(v) == 2.5);

  // ── string_view（回移 C++17 std::string_view）──
  const string_view sv("backport-cpp 1.2.0");
  CHECK(sv.size() == 18u);
  CHECK(sv.substr(0, 9) == string_view("backport-"));
  CHECK(sv[0] == 'b');
  CHECK(sv.find("1.2.0") == 13u);

  // ── span（回移 C++20 std::span）──
  int arr[4] = {1, 2, 3, 4};
  bpstd::span<int> sp(arr);  // 从 C 数组构造（动态 extent）
  CHECK(sp.size() == 4u);
  CHECK(!sp.empty());
  CHECK(sp.front() == 1);
  CHECK(sp.back() == 4);
  CHECK(sp.data() == &arr[0]);

  // ── any（回移 C++17 std::any）──
  bpstd::any a = std::string("hello");
  CHECK(a.type() == typeid(std::string));
  CHECK(bpstd::any_cast<std::string>(a) == "hello");

  // ── tuple ──
  bpstd::tuple<int, string_view> t(1, string_view("x"));
  CHECK(bpstd::get<0>(t) == 1);
  CHECK(bpstd::get<1>(t) == string_view("x"));

  // ── utility::exchange ──
  int ex = 1;
  CHECK(bpstd::exchange(ex, 2) == 1);
  CHECK(ex == 2);

  // ── functional::invoke / not_fn ──
  auto add = [](int x, int y) { return x + y; };
  CHECK(bpstd::invoke(add, 20, 22) == 42);
  auto is_even = [](int x) { return (x % 2) == 0; };
  auto is_odd = bpstd::not_fn(is_even);
  CHECK(is_odd(3));
  CHECK(!is_odd(4));

  // ── iterator::make_reverse_iterator ──
  std::vector<int> vec{1, 2, 3};
  auto rbegin = bpstd::make_reverse_iterator(vec.end());
  CHECK(*rbegin == 3);

  // ── memory::make_unique ──
  auto up = bpstd::make_unique<int>(11);
  CHECK(up != nullptr);
  CHECK(*up == 11);

  // ── type_traits（编译期断言，不计入运行期总数）──
  static_assert(bpstd::enable_if_t<true, int>{0} == 0, "bpstd::enable_if_t");
  static_assert(bpstd::conditional_t<true, int, long>{5} == 5, "bpstd::conditional_t");
  static_assert(bpstd::is_integral<int>::value, "bpstd::is_integral");

  // ── exception::uncaught_exceptions ──
  CHECK(bpstd::uncaught_exceptions() == 0);

  // ── chrono::days ──
  bpstd::chrono::days d(2);
  CHECK(d.count() == 2);

  // ── complex ──
  bpstd::complex<double> c(1.0, 2.0);
  CHECK(c.real() == 1.0);
  CHECK(c.imag() == 2.0);

  // ── string literals operator""_s ──
  using namespace bpstd::literals::string_literals;
  std::string s = "abc"_s;
  CHECK(s == "abc");

  std::printf("PASS: backport-cpp 1.2.0 消费者测试 %d/%d 断言通过\n",
              g_checks - g_failed, g_checks);
  return g_failed == 0 ? 0 : 1;
}
