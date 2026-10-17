#include <cstdint>
#include <iostream>
#include <limits>

#include <SafeInt.hpp>

namespace {
bool check(bool condition, const char* expression, int line) {
  if (!condition) {
    std::cerr << "check failed at line " << line << ": " << expression << '\n';
    return false;
  }
  return true;
}
}  // namespace

#define SAFEINT_CHECK(expression) \
  do { \
    if (!check((expression), #expression, __LINE__)) return 1; \
  } while (false)

int main() {
  SafeInt<std::int32_t> value = 40;
  SAFEINT_CHECK(static_cast<std::int32_t>(value) == 40);
  SAFEINT_CHECK(static_cast<std::int32_t>(value + 2) == 42);
  SAFEINT_CHECK(static_cast<std::int32_t>(value - 8) == 32);
  SAFEINT_CHECK(static_cast<std::int32_t>(value * 5) == 200);
  SAFEINT_CHECK(static_cast<std::int32_t>(value / 4) == 10);
  SAFEINT_CHECK(static_cast<std::int32_t>(value % 7) == 5);

  std::int32_t result = 0;
  SAFEINT_CHECK(SafeCast(std::int64_t{1234}, result) && result == 1234);
  SAFEINT_CHECK(SafeAdd(std::int32_t{100}, std::int32_t{23}, result) && result == 123);
  SAFEINT_CHECK(!SafeAdd(std::numeric_limits<std::int32_t>::max(), 1, result));

  bool caught = false;
  try {
    SafeInt<std::int32_t> maximum = std::numeric_limits<std::int32_t>::max();
    maximum += 1;
  } catch (const SafeIntException& error) {
    caught = error.m_code == SafeIntArithmeticOverflow;
  }
  SAFEINT_CHECK(caught);
  std::cout << "PASS: SafeInt C++ consumer (10/10 checks)\n";
  return 0;
}
