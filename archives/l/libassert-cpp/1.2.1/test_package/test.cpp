#include <assert.hpp>

#include <string>

// Consumer verification: link against assert::assert and exercise the
// ASSERT macro offered by libassert against real runtime conditions.
int main() {
  // Passing assertion: source location machinery + decomposition active.
  int value = 42;
  ASSERT(value == 42);

  // Debug stringification path used by the library's diagnostic printer.
  std::string text = "libassert works";
  ASSERT(text == "libassert works");

  return 0;
}