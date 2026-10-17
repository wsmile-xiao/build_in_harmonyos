// test_package 消费者用例 — bandit 2.0.0 (HarmonyOS PC, aarch64)
// 仅通过已安装的公开头文件 <bandit/bandit.h> 使用 bandit 公开 API，
// 模拟上层应用/测试工程消费该三方库：编译、链接并实际运行。
// 调用公开 API: go_bandit/describe/it/before_each + snowhouse 断言与匹配器。
#include <bandit/bandit.h>
#include <string>
#include <vector>

using namespace bandit;
using namespace snowhouse;

go_bandit([]() {
  describe("bandit consumer usage", [&]() {
    std::vector<int> values;

    before_each([&]() { values = {1, 2, 3, 4, 5}; });

    it("lets a consumer compute observable results with matchers", [&]() {
      int sum = 0;
      for (int v : values) {
        sum += v;
      }
      AssertThat(sum, Equals(15));
      AssertThat(values, Has().OfLength(5));
    });

    it("lets a consumer assert on strings", [&]() {
      std::string greeting = std::string("hello ") + "bandit";
      AssertThat(greeting, StartsWith("hello"));
      AssertThat(greeting, Contains("bandit"));
    });

    it("lets a consumer verify exceptions", [&]() {
      auto boom = []() { throw std::logic_error("consumer boom"); };
      AssertThrows(std::logic_error, boom());
    });
  });
});

int main(int argc, char* argv[])
{
  return bandit::run(argc, argv);
}
