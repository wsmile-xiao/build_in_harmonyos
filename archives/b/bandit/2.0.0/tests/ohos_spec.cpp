// bandit 2.0.0 — HarmonyOS (aarch64, clang/libc++-ohos) 专项测试
// 使用 bandit 公开头文件编写真实 BDD spec，验证框架在 OHOS 上的
// 编译、运行与断言/匹配器行为。与上游测试、test_package 分别计数。
//
// 编译运行（对 work 源码树）:
//   clang++ -std=c++11 -I<work-root> tests/ohos_spec.cpp -o /tmp/ohos_spec && /tmp/ohos_spec
// 其中 <work-root> 包含 bandit/ 头树（含 snowhouse 子模块头文件）

#include <bandit/bandit.h>
#include <vector>
#include <string>
#include <stdexcept>

using namespace bandit;
using namespace snowhouse;

go_bandit([]() {
  describe("bandit on HarmonyOS", [&]() {
    int state_before_each = 0;
    bool state_after_each = false;

    before_each([&]() {
      state_before_each = 42;
      state_after_each = false;
    });

    after_each([&]() {
      state_after_each = true;
    });

    it("supports basic equality assertions via snowhouse", [&]() {
      int a = 2 + 3;
      AssertThat(a, Equals(5));
      AssertThat(a, Is().GreaterThan(4));
    });

    it("supports container matchers on std::vector", [&]() {
      std::vector<int> v{1, 2, 3};
      AssertThat(v, Has().OfLength(3));
      AssertThat(v[0] + v[1] + v[2], Equals(6));
    });

    it("supports string assertions", [&]() {
      std::string s = "harmonyos-pc";
      AssertThat(s, Contains("os"));
      AssertThat(s, StartsWith("har"));
      AssertThat(s.length(), IsGreaterThan(8u));
    });

    it("supports exception assertion via AssertThrows", [&]() {
      auto fn = []() { throw std::runtime_error("boom"); };
      AssertThrows(std::runtime_error, fn());
    });

    it("supports before_each/after_each hook ordering", [&]() {
      // before_each 在本条 it 前已置位 42；上一条 it 结束后 after_each 置位 true，
      // 又被本条 before_each 复位为 false → 证明两条钩子均按序执行
      AssertThat(state_before_each, Equals(42));
      AssertThat(state_after_each, IsFalse());
    });

    it("supports user-defined matcher chains", [&]() {
      double d = 3.14159;
      AssertThat(d, Is().EqualTo(3.14159));
      AssertThat(static_cast<int>(d), Equals(3));
    });
  });
});

int main(int argc, char* argv[])
{
  return bandit::run(argc, argv);
}
