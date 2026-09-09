// celero 2.10.0 consumer smoke test.
//
// 1) Deterministic assertions against the celero::Statistics header API.
// 2) Registers two real micro-benchmarks (explicit small sample/iteration
//    counts to stay fast) and drives the compiled library through
//    celero::Run() — exercising Benchmark/Executor/Statistics/Timer/Print.
#include <celero/Celero.h>
#include <celero/Statistics.h>
#include <celero/Utilities.h>

#include <cmath>
#include <cstdint>
#include <cstdio>

static int g_failures = 0;

static void check(bool ok, const char* what)
{
    if(ok)
    {
        std::printf("[PASS] %s\n", what);
    }
    else
    {
        std::printf("[FAIL] %s\n", what);
        ++g_failures;
    }
}

// 固定小规模：每组 3 个样本 × 100 次迭代，真机冒烟秒级完成
BASELINE(Smoke, Sqrt, 3, 100)
{
    celero::DoNotOptimizeAway(std::sqrt(12345.6789));
}

BENCHMARK(Smoke, InvSqrt, 3, 100)
{
    celero::DoNotOptimizeAway(1.0 / std::sqrt(12345.6789));
}

int main()
{
    // --- celero::Statistics（头文件 API）确定性断言 ---
    celero::Statistics<int64_t> stats;
    stats.addSample(10);
    stats.addSample(20);
    stats.addSample(30);

    check(stats.getSize() == 3, "Statistics::getSize() == 3");
    check(std::fabs(stats.getMean() - 20.0) < 1e-9, "Statistics::getMean() == 20");
    check(stats.getMin() == 10, "Statistics::getMin() == 10");
    check(stats.getMax() == 30, "Statistics::getMax() == 30");
    check(std::fabs(stats.getVariance() - 100.0) < 1e-9, "Statistics::getVariance() == 100");

    // --- 编译库 API：跑两个真实基准 ---
    char arg0[] = "test_celero";
    char* argv[] = {arg0, nullptr};
    celero::Run(1, argv);
    std::printf("[PASS] celero::Run() executed Smoke benchmarks\n");

    if(g_failures > 0)
    {
        std::printf("FAILED: %d assertion(s)\n", g_failures);
        return 1;
    }
    std::printf("All celero smoke checks passed.\n");
    return 0;
}
