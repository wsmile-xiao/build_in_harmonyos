// Real consumer for the taskflow Conan package (R34).
//
// Exercises the public API end to end on OHOS and checks observable
// results instead of only printing:
//   1. work-stealing executor + taskflow graph with precede() edges and
//      blocking run through tf::Future;
//   2. parallel tf::FlowBuilder::for_each / reduce over a 4096-element
//      range with exact expected results;
//   3. repeated large-graph churn (8 rounds x 5000 nodes) that drives the
//      tf::ObjectPool cold path, i.e. the backing allocator adapted by
//      patches/0003 for libc++ versions without <memory_resource>.
#include <taskflow/taskflow.hpp>
// The parallel algorithms live in their own headers (the umbrella header only
// pulls in core + algorithm/algorithm.hpp); upstream unit tests include the
// specific algorithm headers the same way.
#include <taskflow/algorithm/for_each.hpp>
#include <taskflow/algorithm/reduce.hpp>

#include <atomic>
#include <cstdio>
#include <functional>
#include <numeric>
#include <vector>

namespace {

int failures = 0;

void check(bool ok, const char* what) {
  if(!ok) {
    std::printf("FAIL: %s\n", what);
    ++failures;
  }
}

}  // namespace

int main() {

  tf::Executor executor(4);

  // ---- 1. taskflow graph with dependency edges --------------------------
  {
    tf::Taskflow taskflow;
    std::atomic<int> counter{0};

    auto [A, B, C] = taskflow.emplace(
      [&counter]() { counter.fetch_add(1); },
      [&counter]() { counter.fetch_add(1); },
      [&counter]() { counter.fetch_add(1); });

    // A -> B, A -> C dependency edges; B and C may run in parallel.
    A.precede(B, C);

    tf::Future<void> future = executor.run(taskflow);
    future.get();

    check(counter.load() == 3, "graph executed exactly 3 nodes");
    check(executor.num_workers() == 4, "executor reports 4 workers");
  }

  // ---- 2. parallel for_each / reduce ------------------------------------
  {
    constexpr int N = 4096;

    std::vector<int> data(N);
    std::iota(data.begin(), data.end(), 0);

    tf::Taskflow taskflow;
    std::atomic<long long> visited{0};

    taskflow.for_each(data.begin(), data.end(),
      [&visited](int) {
        visited.fetch_add(1, std::memory_order_relaxed);
      });

    long long sum = 0;
    taskflow.reduce(data.begin(), data.end(), sum, std::plus<long long>{});

    executor.run(taskflow).wait();

    check(visited.load() == N, "for_each visited every element");
    check(sum == static_cast<long long>(N) * (N - 1) / 2,
          "reduce produced the exact sum");
  }

  // ---- 3. node-pool churn through the object-pool cold path -------------
  {
    constexpr int ROUNDS = 8;
    constexpr int NODES  = 5000;

    tf::Taskflow taskflow;
    std::atomic<int> ran{0};

    for(int round = 0; round < ROUNDS; ++round) {
      // clear() recycles the previously allocated graph nodes.
      taskflow.clear();
      for(int i = 0; i < NODES; ++i) {
        taskflow.emplace([&ran]() {
          ran.fetch_add(1, std::memory_order_relaxed);
        });
      }
      executor.run(taskflow).wait();
    }

    check(ran.load() == ROUNDS * NODES, "node churn executed every node");
  }

  if(failures != 0) {
    std::printf("taskflow consumer FAILED: %d check(s)\n", failures);
    return 1;
  }

  std::printf("taskflow consumer OK: 5 checks passed "
              "(graph for_each reduce object-pool)\n");
  return 0;
}
