#include <libfork.hpp>

#include <optional>
#include <span>

using lf::call;
using lf::fork;
using lf::join;
using lf::task;

inline constexpr auto fib = [](auto fib, int n) -> task<int> {
  if (n < 2) {
    co_return n;
  }

  int a, b;

  co_await fork(&a, fib)(n - 1);
  co_await call(&b, fib)(n - 2);

  co_await join;

  co_return a + b;
};

auto main() -> int {
  // Upstream single-header self-check: fib(10) == 55 via lazy_pool.
  int const fib_10 = lf::sync_wait(lf::lazy_pool{}, fib, 10);
  if (fib_10 != 55) {
    return 1;
  }

  // Exercise the empty-range path of lf::fold (returns nullopt).
  std::span<int> empty_span;
  if (lf::sync_wait(lf::lazy_pool{}, lf::fold, empty_span, std::plus<>{}) != std::nullopt) {
    return 2;
  }

  return 0;
}
