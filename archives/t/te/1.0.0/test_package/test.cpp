#include <sstream>
#include <string>

#include <boost/te.hpp>

namespace te = boost::te;

// Minimal real usage of the te API: a type-erased drawable, exactly the
// canonical pattern from the upstream README/example (drawable.cpp).
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

static int failures = 0;
#define expect(...) \
  (void)((__VA_ARGS__) || (++failures, 0))

int main() {
  std::ostringstream out{};

  te::poly<Drawable> drawable{Square{}};
  drawable.draw(out);
  expect(out.str() == "Square");
  out.str("");

  drawable = Circle{};
  drawable.draw(out);
  expect(out.str() == "Circle");
  out.str("");

  // shared storage + copy semantics
  te::poly<Drawable, te::shared_storage> shared{Square{}};
  auto copy = shared;
  copy.draw(out);
  expect(out.str() == "Square");

  if (failures != 0) {
    return 1;
  }
  return 0;
}
