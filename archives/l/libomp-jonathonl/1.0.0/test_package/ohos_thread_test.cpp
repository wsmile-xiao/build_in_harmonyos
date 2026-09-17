#include "omp.hpp"

#include <pthread.h>
#include <sched.h>

#include <atomic>
#include <cstddef>
#include <iostream>
#include <vector>

#ifndef __OHOS__
#error "This HarmonyOS-specific test requires the OHOS compiler target"
#endif

#ifndef __aarch64__
#error "This HarmonyOS PC test requires the AArch64 target"
#endif

namespace {

int failures = 0;
int checks = 0;

void check(bool condition, const char *description) {
  ++checks;
  if (!condition) {
    ++failures;
    std::cerr << "FAILED: " << description << '\n';
  }
}

}  // namespace

int main() {
  check(sizeof(void *) == 8, "HarmonyOS PC uses the 64-bit AArch64 ABI");

  std::atomic<unsigned> parallel_calls{0};
  std::atomic<unsigned> pthread_errors{0};
  std::atomic<unsigned> invalid_policies{0};

  // Exercise the zero sentinel that selects hardware_concurrency(). Upstream
  // 1.0.0 used that zero in reserve(), causing unsigned underflow/bad_alloc.
  omp::parallel(
      [&](std::size_t) {
        int policy = -1;
        sched_param parameters{};
        if (pthread_getschedparam(pthread_self(), &policy, &parameters) != 0) {
          pthread_errors.fetch_add(1, std::memory_order_relaxed);
        } else if (policy != SCHED_OTHER && policy != SCHED_FIFO &&
                   policy != SCHED_RR) {
          invalid_policies.fetch_add(1, std::memory_order_relaxed);
        }
        parallel_calls.fetch_add(1, std::memory_order_relaxed);
      });

  check(parallel_calls.load(std::memory_order_relaxed) > 0,
        "default omp::parallel executed workers");
  check(pthread_errors.load(std::memory_order_relaxed) == 0,
        "OHOS pthread scheduler metadata is available");
  check(invalid_policies.load(std::memory_order_relaxed) == 0,
        "OHOS pthread scheduler policy is recognized");

  std::vector<int> values(64, 0);
  std::atomic<unsigned> visits{0};
  std::atomic<unsigned> bad_indexes{0};
  omp::parallel_for(
      omp::dynamic_schedule(3), values.begin(), values.end(),
      [&](int &value, const omp::iteration_context &ctx) {
        value = static_cast<int>(ctx.index + 1);
        if (ctx.index >= values.size()) {
          bad_indexes.fetch_add(1, std::memory_order_relaxed);
        }
        visits.fetch_add(1, std::memory_order_relaxed);
      },
      4);

  check(visits.load(std::memory_order_relaxed) == values.size(),
        "dynamic scheduler visited every item exactly once");
  check(bad_indexes.load(std::memory_order_relaxed) == 0,
        "iteration indexes stayed in range");
  bool values_match = true;
  for (std::size_t i = 0; i < values.size(); ++i) {
    values_match = values_match && values[i] == static_cast<int>(i + 1);
  }
  check(values_match, "iteration index matched the mutated element");

  unsigned critical_total = 0;
  omp::parallel(
      [&](std::size_t) {
        omp::critical([&critical_total]() { ++critical_total; });
      },
      4);
  check(critical_total == 4, "global critical section serialized updates");

  std::cout << "libomp-jonathonl HarmonyOS checks passed: "
            << (checks - failures) << '/' << checks << '\n';
  return failures == 0 ? 0 : 1;
}
