#include <cstdint>
#include <iostream>
#include <ewah/boolarray.h>
#include <ewah/ewah.h>

int main() {
  using Bitmap = ewah::EWAHBoolArray<uint32_t>;
  int failures = 0;
  const auto check = [&failures](bool condition, const char *name) {
    if (!condition) {
      std::cerr << "FAIL: " << name << '\n';
      ++failures;
    }
  };

  Bitmap left = Bitmap::bitmapOf(4, 1, 2, 100, 1000);
  Bitmap right = Bitmap::bitmapOf(4, 2, 3, 1000, 2000);
  check(!Bitmap().get(1), "default bitmap is empty");
  check(left.get(100) && !left.get(101), "set/get");
  check((left | right).numberOfOnes() == 6, "union cardinality");
  check((left & right).numberOfOnes() == 2, "intersection cardinality");
  check((left - right).numberOfOnes() == 2, "difference cardinality");
  check((left ^ right).numberOfOnes() == 4, "xor cardinality");
  check(left.intersects(right) && !left.intersects(Bitmap::bitmapOf(1, 3000)),
        "intersects");

  ewah::BoolArray<uint32_t> dense = ewah::BoolArray<uint32_t>::bitmapOf(2, 4, 8);
  check(dense.numberOfOnes() == 2 && dense.get(8), "BoolArray consumer API");

  return failures == 0 ? 0 : 1;
}
