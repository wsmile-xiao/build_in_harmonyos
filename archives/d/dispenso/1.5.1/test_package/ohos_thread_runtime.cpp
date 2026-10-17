#include <dispenso/dispenso.h>

#include <pthread.h>
#include <sched.h>

#include <atomic>
#include <iostream>

#ifndef __OHOS__
#error "This test must be compiled by the HarmonyOS toolchain"
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

} // namespace

int main() {
  constexpr int kTaskCount = 64;
  std::atomic<int> completed{0};
  std::atomic<int> pthread_errors{0};
  std::atomic<int> invalid_policies{0};

  dispenso::ThreadPool pool(2);
  dispenso::TaskSet tasks(pool);
  for (int i = 0; i < kTaskCount; ++i) {
    tasks.schedule([&]() {
      int policy = -1;
      sched_param parameters{};
      if (pthread_getschedparam(pthread_self(), &policy, &parameters) != 0) {
        pthread_errors.fetch_add(1, std::memory_order_relaxed);
      } else if (policy != SCHED_OTHER && policy != SCHED_FIFO &&
                 policy != SCHED_RR) {
        invalid_policies.fetch_add(1, std::memory_order_relaxed);
      }
      completed.fetch_add(1, std::memory_order_relaxed);
    });
  }

  check(pool.numThreads() == 2, "OHOS worker pool size");
  check(!tasks.wait(), "OHOS task set completed without cancellation");
  check(completed.load(std::memory_order_relaxed) == kTaskCount,
        "all tasks executed on OHOS pthread workers");
  check(pthread_errors.load(std::memory_order_relaxed) == 0,
        "OHOS pthread scheduler metadata available");
  check(invalid_policies.load(std::memory_order_relaxed) == 0,
        "OHOS pthread scheduler policy recognized");

  std::cout << "Dispenso HarmonyOS pthread checks passed: " << checks << '/'
            << checks << '\n';
  return failures == 0 ? 0 : 1;
}
