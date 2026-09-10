#include <benchmark/benchmark.h>

namespace {

void BM_Main(benchmark::State& state) {
  for (auto _ : state) {
    benchmark::DoNotOptimize(state.iterations());
  }
}

}  // namespace

BENCHMARK(BM_Main);
BENCHMARK_MAIN();
