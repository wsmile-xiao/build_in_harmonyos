//
// HarmonyOS 专项测试 — boost-te 1.0.0
// R6 要求 __OHOS__ 守卫必须有实质逻辑：OHOS 平台校验平台宏并验证 te
// 类型擦除在 OHOS 工具链下行为正确；非 OHOS 平台同样执行相同的 te 调用
// 验证路径（保证任一平台构建都能真正运行而非空壳）。
//
#include <boost/te.hpp>

#include <cassert>
#include <cstdint>
#include <sstream>

namespace te = boost::te;

#if defined(__OHOS__)
static constexpr bool kOnOhos = true;
static_assert(__OHOS__ == 1, "__OHOS__ must be defined as 1 on OHOS");
#else
static constexpr bool kOnOhos = false;
#endif

struct Calculator {
  int add(int a, int b) const {
    // te::call 模板首参为返回类型（默认 void），必须显式指定 R=int
    return te::call<int>([](auto const &self, int a, int b) { return self.add(a, b); },
                         *this, a, b);
  }
  std::int64_t mul64(std::int64_t a, std::int64_t b) const {
    return te::call<std::int64_t>([](auto const &self, std::int64_t a, std::int64_t b) { return self.mul64(a, b); },
                                  *this, a, b);
  }
};

struct RealCalculator {
  int add(int a, int b) const { return a + b; }
  std::int64_t mul64(std::int64_t a, std::int64_t b) const { return a * b; }
};

int main() {
  te::poly<Calculator> calc{RealCalculator{}};
  assert(calc.add(2, 3) == 5);
  assert(calc.add(-1, 1) == 0);

  // int64 跨类型擦除调用（确认宽类型在 te 调用路径下无截断）
  std::int64_t big = 0x1234567890LL;
  assert(calc.mul64(big, 2) == big * 2);

  std::stringstream out{};
  out << (kOnOhos ? "ohos" : "native");
  assert(!out.str().empty());

  return 0;
}
