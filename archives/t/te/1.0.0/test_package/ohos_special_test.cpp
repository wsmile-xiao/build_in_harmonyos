// OHOS 专项测试：验证 te 类型擦除在 OHOS SDK libc++ (aarch64-linux-ohos) 下的
// 存储策略与运行时行为。独立于上游 test/te.cpp 的最小可执行用例。
#include <cstdio>
#include <cstdlib>
#include <sstream>
#include <string>
#include <type_traits>

#include <boost/te.hpp>

namespace te = boost::te;

struct Drawable {
  void draw(std::ostream &out) const {
    te::call([](auto const &self, auto &out) { self.draw(out); }, *this, out);
  }
};

struct Square {
  void draw(std::ostream &out) const { out << "Square"; }
};

int main() {
  int failures = 0;

  // 1) local_storage 策略在 OHOS libc++ 下工作（默认 32 字节小对象缓冲）
  te::poly<Drawable, te::local_storage<32>> p{Square{}};
  std::ostringstream os{};
  p.draw(os);
  if (os.str() != "Square") {
    std::printf("FAIL local_storage: %s\n", os.str().c_str());
    ++failures;
  }

  // 2) shared_storage 拷贝语义
  te::poly<Drawable, te::shared_storage> s{Square{}};
  auto c = s;
  std::ostringstream os2{};
  c.draw(os2);
  if (os2.str() != "Square") {
    std::printf("FAIL shared_storage copy\n");
    ++failures;
  }

  // 3) 空 poly 状态与重新赋值
  te::poly<Drawable> d{Square{}};
  d = Square{};
  std::ostringstream os3{};
  d.draw(os3);
  if (os3.str() != "Square") {
    std::printf("FAIL reassign\n");
    ++failures;
  }

  if (failures == 0) {
    std::printf("OHOS special test: all passed\n");
    return 0;
  }
  std::printf("OHOS special test: %d failure(s)\n", failures);
  return 1;
}
