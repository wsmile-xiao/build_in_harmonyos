#include <benchmark/benchmark.h>

#include <cstddef>

namespace {

void BM_Consumer(benchmark::State& state) {
  std::size_t value = 1;
  for (auto _ : state) {
    value = value * 3U + 1U;
    benchmark::DoNotOptimize(value);
  }
  benchmark::DoNotOptimize(value);
}

}  // namespace

BENCHMARK(BM_Consumer);

int main(int argc, char** argv) {
  benchmark::Initialize(&argc, argv);
  if (benchmark::ReportUnrecognizedArguments(argc, argv)) {
    return 2;
  }
  const std::size_t count = benchmark::RunSpecifiedBenchmarks();
  benchmark::Shutdown();
  return count == 1U ? 0 : 1;
}
