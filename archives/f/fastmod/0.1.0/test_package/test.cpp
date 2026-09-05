// Consumer-side API test: verify the installed header and CMake target.
#include <cstdint>
#include <iostream>

#include "fastmod.h"

namespace {
bool check(bool condition, const char* expression, int line) {
  if (!condition) {
    std::cerr << "check failed at line " << line << ": " << expression << '\n';
    return false;
  }
  return true;
}
}  // namespace

#define FASTMOD_CHECK(expression) \
  do { \
    if (!check((expression), #expression, __LINE__)) return 1; \
  } while (false)

int main() {
  const uint32_t unsigned_divisor = 7;
  const uint64_t unsigned_multiplier =
      fastmod::computeM_u32(unsigned_divisor);
  FASTMOD_CHECK(fastmod::fastmod_u32(100, unsigned_multiplier, unsigned_divisor) == 2);
  FASTMOD_CHECK(fastmod::fastdiv_u32(100, unsigned_multiplier) == 14);
  FASTMOD_CHECK(fastmod::is_divisible(98, unsigned_multiplier));
  FASTMOD_CHECK(!fastmod::is_divisible(100, unsigned_multiplier));

  const int32_t signed_divisor = -5;
  const uint64_t signed_multiplier = fastmod::computeM_s32(signed_divisor);
  FASTMOD_CHECK(fastmod::fastmod_s32(-100, signed_multiplier, 5) == 0);
  FASTMOD_CHECK(fastmod::fastmod_s32(-101, signed_multiplier, 5) == -1);
  FASTMOD_CHECK(fastmod::fastdiv_s32(-101, signed_multiplier, signed_divisor) == 20);

  FASTMOD_CHECK(fastmod::fastmod<7>(100) == 2);
  FASTMOD_CHECK(fastmod::fastdiv<7>(100) == 14);
  FASTMOD_CHECK(fastmod::fastmod<5>(-101) == -1);
  FASTMOD_CHECK(fastmod::fastdiv<-5>(-101) == 20);
  return 0;
}
