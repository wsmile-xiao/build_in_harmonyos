#include <cstdint>
#include <iostream>
#include <limits>

#include <SafeInt.hpp>

#ifndef __OHOS__
#error "This test must be compiled by the HarmonyOS toolchain"
#endif

namespace {
bool check(bool condition, const char* expression, int line) {
  if (!condition) {
    std::cerr << "OHOS check failed at line " << line << ": " << expression << '\n';
    return false;
  }
  return true;
}
}  // namespace

#define OHOS_CHECK(expression) \
  do { \
    if (!check((expression), #expression, __LINE__)) return 1; \
  } while (false)

int main() {
  OHOS_CHECK(sizeof(void*) == 8);
  OHOS_CHECK(sizeof(long) == 8);
  OHOS_CHECK(SAFEINT_COMPILER == CLANG_COMPILER);
  OHOS_CHECK(SAFEINT_HAS_INT128 == 1);

  std::uint64_t result = 0;
  const std::uint64_t half = std::numeric_limits<std::uint64_t>::max() / 2;
  OHOS_CHECK(SafeMultiply(half, std::uint64_t{2}, result));
  OHOS_CHECK(result == std::numeric_limits<std::uint64_t>::max() - 1);
  OHOS_CHECK(!SafeMultiply(std::numeric_limits<std::uint64_t>::max(),
                           std::uint64_t{2}, result));
  std::cout << "PASS: HarmonyOS aarch64 SafeInt platform test (7/7 checks)\n";
  return 0;
}
