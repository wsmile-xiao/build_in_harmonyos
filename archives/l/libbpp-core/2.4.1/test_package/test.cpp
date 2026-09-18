#include <Bpp/Numeric/Range.h>
#include <iostream>
#include <string>

using namespace bpp;

// 5 real checks against the packaged bpp-core library.
int main() {
  int passed = 0;

  // 1. Range construction + bounds.
  Range<unsigned int> r1(3, 6);
  if (r1.begin() != 3 || r1.end() != 6) {
    std::cerr << "range bounds mismatch" << std::endl;
    return 1;
  }
  ++passed;

  // 2. Overlap: [3,6[ overlaps [0,5[.
  Range<unsigned int> r4(0, 5);
  if (!r1.overlap(r4)) {
    std::cerr << "expected overlap" << std::endl;
    return 2;
  }
  ++passed;

  // 3. No overlap: [3,6[ vs [10,12[.
  Range<unsigned int> r2(10, 12);
  if (r1.overlap(r2)) {
    std::cerr << "unexpected overlap" << std::endl;
    return 3;
  }
  ++passed;

  // 4. Expand: [3,6[ \/ [0,5[ == [0,6[.
  Range<unsigned int> r = r1;
  r.expandWith(r4);
  if (r != Range<unsigned int>(0, 6)) {
    std::cerr << "expand mismatch: " << r.toString() << std::endl;
    return 4;
  }
  ++passed;

  // 5. toString is non-empty and stable.
  std::string s = r1.toString();
  if (s.empty()) {
    std::cerr << "empty toString" << std::endl;
    return 5;
  }
  ++passed;

  std::cout << "libbpp-core consumer checks passed: " << passed << "/5"
            << " toString=" << s << std::endl;
  return 0;
}
