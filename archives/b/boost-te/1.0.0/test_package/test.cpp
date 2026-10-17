//
// test_package consumer test — boost-te 1.0.0
// Verifies the shipped header compiles and the te type-erasure API actually
// works (R34: must exercise the real API, not a print-only stub).
// API 用法对齐上游 README：te::poly<Interface>{Concrete{}} 隐式构造 + te::call。
//
#include <boost/te.hpp>

#include <cassert>
#include <sstream>
#include <string>

namespace te = boost::te;

struct Drawable {
  void draw(std::ostream &out) const {
    te::call([](auto const &self, auto &out) { self.draw(out); }, *this, out);
  }
};

struct Square {
  void draw(std::ostream &out) const { out << "Square"; }
};

struct Circle {
  void draw(std::ostream &out) const { out << "Circle"; }
};

void draw_it(te::poly<Drawable> const &drawable, std::ostream &out) {
  drawable.draw(out);
}

int main() {
  std::stringstream out{};
  te::poly<Drawable> drawable{Square{}};
  drawable.draw(out);
  assert(out.str() == "Square");

  out.str("");
  te::poly<Drawable> drawable2{Circle{}};
  draw_it(drawable2, out);
  assert(out.str() == "Circle");

  // 常量引用传递擦除对象（README 经典用法）
  out.str("");
  draw_it(drawable, out);
  assert(out.str() == "Square");

  return 0;
}
