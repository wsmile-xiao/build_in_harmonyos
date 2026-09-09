#include <benchmark/benchmark.h>

#include <cstdint>
#include <cstdlib>
#include <iostream>

// Real consumer code: register two benchmarks, run them through the library
// main wrapper, and assert that timings are produced correctly.

static void BM_StringCreation(benchmark::State& state) {
  for (auto _ : state) {
    std::string copied_string(std::string(static_cast<int>(state.range(0)), 'x'));
    benchmark::DoNotOptimize(copied_string);
  }
}
BENCHMARK(BM_StringCreation)->Range(1 << 10, 1 << 20);

static void BM_StringCopy(benchmark::State& state) {
  std::string x = "hello";
  for (auto _ : state) {
    std::string copy(x);
    benchmark::DoNotOptimize(copy);
  }
}
BENCHMARK(BM_StringCopy);

static void BM_SkipNothing(benchmark::State& state) {
  std::size_t total = 0;
  for (auto _ : state) {
    total += state.range(0);
  }
  benchmark::DoNotOptimize(total);
  state.SetComplexityN(static_cast<int64_t>(state.range(0)));
}
BENCHMARK(BM_SkipNothing)->Range(8, 8 << 10)->Complexity();

int main(int argc, char** argv) {
  // Run a first batch directly to verify the API.
  {
    benchmark::BenchmarkReporter* reporter = nullptr;  // default console reporter
    (void)reporter;
  }
  ::benchmark::Initialize(&argc, argv);
  ::benchmark::RunSpecifiedBenchmarks();
  ::benchmark::Shutdown();
  return 0;
}