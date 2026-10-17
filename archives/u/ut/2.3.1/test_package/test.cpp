// test_package 消费者测试 — 真实 include 并使用 boost/ut.hpp（R34）
#include <boost/ut.hpp>
#include <string>

int main() {
  using namespace boost::ut;

  "consumer test"_test = [] {
    expect(42_i == 42);
    std::string s{"harmonyos"};
    expect(s.size() == 9_u);
  };

  return 0;
}
