#include <continuable/continuable.hpp>

#include <cstdio>
#include <exception>
#include <stdexcept>

namespace {

int check(bool condition) {
  return condition ? 0 : 1;
}

}  // namespace

int main() {
  int failures = 0;

  auto chained = cti::make_ready_continuable(21)
                     .then([](int value) { return value * 2; })
                     .apply(cti::transforms::to_future());
  failures += check(chained.get() == 42);

  auto combined = cti::when_all(cti::make_ready_continuable(4),
                                cti::make_ready_continuable(5))
                      .then([](int left, int right) { return left + right; })
                      .apply(cti::transforms::to_future());
  failures += check(combined.get() == 9);

  bool handled = false;
  auto recovered = cti::make_exceptional_continuable<int>(
                       std::make_exception_ptr(std::runtime_error("expected")))
                       .fail([&handled](std::exception_ptr error) {
                         handled = static_cast<bool>(error);
                         return cti::make_ready_continuable(7);
                       })
                       .apply(cti::transforms::to_future());
  failures += check(handled && recovered.get() == 7);

  if (failures != 0) {
    std::printf("continuable test_package: %d/3 checks passed\n", 3 - failures);
    return 1;
  }
  std::printf("continuable test_package: 3/3 checks passed\n");
  return 0;
}
