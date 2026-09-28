// kitten 0.1.0 — 消费者测试（test_package / L1）
//
// 从**已安装包头** `#include <kitten/...>` 取用（不是源码树），覆盖 kitten 的四类
// 实例面：functor（std::optional / std::vector / std::deque / std::list）、
// monad（`>>`、wrap）、applicative（`+`、pure）、function_wrapper 组合（`fn|fn`）
// 与 multifunctor（std::variant 的 `||`）。其中第 12 项专门覆盖
// `liftF<别名模板>`——上游 0.1.0 在 clang（鸿蒙唯一可用编译器）下因 SFINAE 守卫按
// 模板身份判定而不可编译，本包补丁修复后该路径可正常求值。
//
// 显式计数、任一失败即进程非零退出；不依赖 assert/NDEBUG（-DNDEBUG 下同样生效）。
// 这是「鸿蒙特有测试」行的用例来源（不进上游用例分母），输出形态：
//   kitten consumer checks: N run, M failed

#include <kitten/kitten.h>

#include <kitten/instances/function.h>
#include <kitten/instances/optional.h>
#include <kitten/instances/sequence_container.h>
#include <kitten/instances/variant.h>

#include <deque>
#include <list>
#include <optional>
#include <string>
#include <variant>
#include <vector>

#include <iostream>

namespace kit = rvarago::kitten;
using kit::types::fn;

namespace {

int checks = 0;
int failed = 0;

void expect(bool cond, const char* what, int line) {
  ++checks;
  if (!cond) {
    ++failed;
    std::cerr << "[FAIL] line " << line << ": " << what << "\n";
  }
}

// 测试用的别名模板（与上游 tests/sequence_container_test.cpp 同形）：
// clang 不把 alias 模板规范化为模板模板实参，是本包补丁的靶点。
template <typename T, typename Allocator = std::allocator<T>>
using SeqAlias = std::vector<T, Allocator>;

}  // namespace

// 括号包裹：宏实参里含花括号初始化列表（逗号）时必须整体再套一层括号
#define EXPECT(cond) expect(static_cast<bool>(cond), #cond, __LINE__)

int main() {
  // kitten 的运算符（`|`、`>>`、`+`、`||`）定义在 rvarago::kitten 内，与上游
  // tests/*.cpp 同形按 using-directive 引入（ADL 找不到：实参都是 std 类型）。
  using namespace rvarago::kitten;

  // ── functor / monad / applicative：std::optional ──────────────────────
  {
    std::optional<int> const some{21};
    std::optional<int> const none{};
    auto doubled = some | [](int v) { return v * 2; };
    EXPECT((doubled.has_value() && *doubled == 42));                                 // 1
    auto doubled_none = none | [](int v) { return v * 2; };
    EXPECT((!doubled_none.has_value()));                                             // 2

    auto bound = some >> [](int v) { return std::optional<std::string>{std::to_string(v)}; };
    EXPECT((bound.has_value() && *bound == "21"));                                   // 3
    auto bound_none = none >> [](int v) { return std::optional<std::string>{std::to_string(v)}; };
    EXPECT((!bound_none.has_value()));                                               // 4

    auto wrapped = kit::wrap<std::optional>(7);
    EXPECT((wrapped.has_value() && *wrapped == 7));                                  // 5
    auto combined = std::optional<int>{2} + std::optional<int>{3};
    EXPECT((combined.has_value() && *combined == 5));                                // 6
    auto purified = kit::pure<std::optional>(9);
    EXPECT((purified.has_value() && *purified == 9));                                // 7
  }

  // ── functor：function_wrapper 组合 ─────────────────────────────────────
  {
    auto composed = fn([](double v) { return static_cast<int>(v); })
                    | fn([](int v) { return std::to_string(v); });
    EXPECT((composed(3.14) == "3"));                                                 // 8
  }

  // ── functor / applicative：std::vector（上游主测容器） ─────────────────
  {
    std::vector<int> const nums{1, 2};
    std::vector<int> const empty;
    auto strings = nums | [](int v) { return std::to_string(v); };
    EXPECT((strings == std::vector<std::string>{"1", "2"}));                         // 9
    EXPECT(((empty | [](int v) { return std::to_string(v); }).empty()));             // 10

    auto lifted = kit::liftF<std::vector>([](int v) { return std::to_string(v); });
    EXPECT((lifted(nums) == std::vector<std::string>{"1", "2"}));                    // 11

    // 别名模板形态（本包补丁修复的路径）
    auto lifted_alias = kit::liftF<SeqAlias>([](int v) { return std::to_string(v); });
    EXPECT((lifted_alias(SeqAlias<int>{10, 20})
            == std::vector<std::string>{"10", "20"}));                               // 12

    auto purified = kit::pure<std::vector>(7);
    EXPECT((purified == std::vector<int>{7}));                                       // 13
  }

  // ── functor：std::deque / std::list（配方守卫覆盖的另两个容器） ─────────
  {
    std::deque<int> const dq{1, 2};
    EXPECT(((dq | [](int v) { return std::to_string(v); })
            == std::deque<std::string>{"1", "2"}));                                  // 14
    std::list<int> const lst{3, 4};
    EXPECT(((lst | [](int v) { return v + 1; }) == std::list<int>{4, 5}));           // 15
  }

  // ── multifunctor：std::variant ─────────────────────────────────────────
  {
    using var_t = std::variant<int, std::string>;
    auto mapper = kit::syntax::overloaded{[](int v) { return v * 10; },
                                          [](std::string const& s) { return s + "!"; }};
    var_t const as_int{7};
    var_t const as_str{std::string{"hi"}};
    auto mapped_int = as_int || mapper;
    auto mapped_str = as_str || mapper;
    EXPECT((std::holds_alternative<int>(mapped_int) && std::get<int>(mapped_int) == 70));  // 16
    EXPECT((std::holds_alternative<std::string>(mapped_str)
            && std::get<std::string>(mapped_str) == "hi!"));                         // 17
  }

  // ── 实例 trait 自证（聚合头 kitten.h 与各实例头可被消费者包含） ─────────
  {
    EXPECT(kit::traits::is_functor_v<std::optional>);                                // 18
    EXPECT((kit::traits::is_monad_v<std::vector>));                                  // 19
    EXPECT((kit::traits::is_applicative_v<std::deque>));                             // 20
    EXPECT((kit::traits::is_multifunctor_v<std::variant>));                          // 21
  }

  std::cout << "kitten consumer checks: " << checks << " run, " << failed << " failed\n";
  return failed == 0 ? 0 : 1;
}
