#include "omp.hpp"

#include <cassert>
#include <cstdlib>
#include <iostream>

int main() {
  std::vector<double> arr(257, 0.0);
  std::mutex named_section;
  std::size_t total = 0;

  omp::internal::thread_pool2 pool(8);
  omp::parallel_for_exp(
      omp::static_schedule(), arr.begin(), arr.end(),
      [&total, &named_section](double &element,
                               const omp::iteration_context &ctx) {
        element = ctx.index + 1;
        omp::critical(named_section, [&total]() { ++total; });
        {
          std::lock_guard<std::mutex> critical(named_section);
        }
        omp::critical([]() {});
      },
      pool);

  omp::parallel_for(
      omp::dynamic_schedule(), omp::sequence_iterator(-2),
      omp::sequence_iterator(5),
      [&total, &named_section](int &, const omp::iteration_context &) {
        std::lock_guard<std::mutex> critical(named_section);
        ++total;
      },
      3);

  std::cout << total << '\n';
  assert(total == 264);
  omp::parallel([](std::size_t) {}, 8);
  return total == 264 ? EXIT_SUCCESS : EXIT_FAILURE;
}
