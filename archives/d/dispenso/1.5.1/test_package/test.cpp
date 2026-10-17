#include <dispenso/detail/per_thread_info.h>
#include <dispenso/dispenso.h>

#include <atomic>
#include <cstddef>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

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
  check(DISPENSO_MAJOR_VERSION == 1, "major version");
  check(DISPENSO_MINOR_VERSION == 5, "minor version");
  check(DISPENSO_PATCH_VERSION == 1, "patch version");

  dispenso::ThreadPool pool(2);
  check(pool.numThreads() == 2, "custom thread pool size");

  std::atomic<int> task_sum{0};
  dispenso::TaskSet tasks(pool);
  for (int i = 0; i < 10; ++i) {
    tasks.schedule(
        [&task_sum, i]() { task_sum.fetch_add(i, std::memory_order_relaxed); });
  }
  check(!tasks.wait(), "task set completed without cancellation");
  check(task_sum.load(std::memory_order_relaxed) == 45, "task set sum");

  std::vector<int> squares(64, -1);
  dispenso::ParForOptions options;
  options.maxThreads = 2;
  dispenso::parallel_for(
      std::size_t{0}, squares.size(),
      [&squares](std::size_t index) {
        squares[index] = static_cast<int>(index * index);
      },
      options);
  check(squares.front() == 0, "parallel_for first result");
  check(squares[7] == 49, "parallel_for middle result");
  check(squares.back() == 3969, "parallel_for final result");
  check(std::accumulate(squares.begin(), squares.end(), 0) == 85344,
        "parallel_for aggregate result");

  dispenso::ConcurrentVector<int> values{3, 5, 8};
  check(values.size() == 3, "concurrent vector size");
  check(values[0] + values[1] + values[2] == 16, "concurrent vector contents");

  bool task_exception_rethrown = false;
  {
    dispenso::TaskSet throwing_tasks(pool);
    throwing_tasks.schedule([]() { throw std::logic_error("task failure"); },
                            dispenso::ForceQueuingTag());
    try {
      throwing_tasks.wait();
    } catch (const std::logic_error &error) {
      task_exception_rethrown = std::string(error.what()) == "task failure";
    } catch (...) {
    }
  }
  check(task_exception_rethrown, "task set wait rethrows task exception");

  bool pipeline_exception_rethrown = false;
  try {
    dispenso::pipeline(
        pool,
        [generated = false]() mutable -> dispenso::OpResult<int> {
          if (generated) {
            return {};
          }
          generated = true;
          return 1;
        },
        dispenso::stage(
            [](int) { throw std::runtime_error("pipeline failure"); }, 1));
  } catch (const std::runtime_error &error) {
    pipeline_exception_rethrown =
        std::string(error.what()) == "pipeline failure";
  } catch (...) {
  }
  check(pipeline_exception_rethrown,
        "serial pipeline stage rethrows in consumer module");

  constexpr int kDeepPipelineItems = 96;
  std::atomic<int> processed{0};
  std::atomic<int> max_inline_depth{0};
  dispenso::pipeline(
      pool,
      [next = 0]() mutable -> dispenso::OpResult<int> {
        if (next == kDeepPipelineItems) {
          return {};
        }
        return next++;
      },
      dispenso::stage(
          [&processed, &max_inline_depth](int) {
            const int depth =
                dispenso::detail::PerPoolPerThreadInfo::inlineDepth();
            int observed = max_inline_depth.load(std::memory_order_relaxed);
            while (observed < depth &&
                   !max_inline_depth.compare_exchange_weak(
                       observed, depth, std::memory_order_relaxed)) {
            }
            processed.fetch_add(1, std::memory_order_relaxed);
          },
          1));
  check(processed.load(std::memory_order_relaxed) == kDeepPipelineItems,
        "deep serial pipeline completes every item");
  check(max_inline_depth.load(std::memory_order_relaxed) ==
            dispenso::detail::kMaxInlineDepth,
        "deep serial pipeline enforces inline depth limit");

  std::cout << "Dispenso consumer API checks passed: " << checks << '/'
            << checks << '\n';
  return failures == 0 ? 0 : 1;
}
