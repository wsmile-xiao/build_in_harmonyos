// test_ohos.cpp — libtnt 1.2.6 鸿蒙特有测试
//
// 针对 OHOS 平台与 libtnt 的真实交点（区别于纯 C++ 语义的组件冒烟）：
//   ① Stopwatch 时钟路径：TNT::Stopwatch 底层是 <time.h> 的 clock()，
//      在 OHOS musl libc 上实测进程 CPU 时钟真实推进（计时 > 0 且
//      量级合理），CLOCKS_PER_SEC 常量合法；
//   ② 真机堆上大数组：512×512 double（2MB，跨数百页）在 OHOS 用户态
//      堆分配/逐页写入/读取校验——数值库典型工作集的页级行为；
//   ③ aarch64 FPU 浮点语义：matmult 非可精确表示小数的累加误差落界
//      （1e-12），验证 OHOS aarch64 + libc++ 浮点行为与解析解一致。
// 自定义 CHECK 宏（-DNDEBUG 下不被剔除），6 项断言，退出码判定。
#include <cmath>
#include <iostream>

#include <tnt.h>

static int g_failures = 0;

#define CHECK(cond)                                                          \
    do {                                                                     \
        if (!(cond)) {                                                       \
            std::cerr << "CHECK FAILED @" << __LINE__ << ": " #cond "\n";    \
            ++g_failures;                                                    \
        }                                                                    \
    } while (0)

// 阻止编译器把空循环优化掉的真实工作负载
static double busy_work(int n) {
    volatile double sink = 0.0;
    for (int i = 1; i <= n; ++i) {
        sink = sink + 1.0 / static_cast<double>(i);
    }
    return sink;
}

int main() {
    // ── ① Stopwatch 时钟路径（OHOS musl clock()/CLOCKS_PER_SEC）──
    CHECK(CLOCKS_PER_SEC > 0);            // musl 提供的时钟分辨率常量合法

    TNT::Stopwatch sw;
    sw.start();
    busy_work(3000000);                   // ~百万次除加，足够让 CPU 时钟推进
    double elapsed = sw.stop();

    CHECK(elapsed > 0.0);                 // 进程 CPU 时钟真实推进（非恒 0）
    CHECK(elapsed < 60.0);                // 量级合理性上界（远小于墙钟超时）

    // ── ② 真机堆上大数组（2MB，跨页分配/写入/读取）──
    const int N = 512;
    TNT::Array2D<double> big(N, N, 0.0);
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N; ++j)
            big[i][j] = static_cast<double>(i) * static_cast<double>(j);
    CHECK(big[N - 1][N - 1] == static_cast<double>((N - 1) * (N - 1)));

    // 全量和为精确整数（(Σi)(Σj)，< 2^53 可精确表示），逐元素累加不丢精度
    double total = 0.0;
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N; ++j)
            total += big[i][j];
    const double half = static_cast<double>(N * (N - 1) / 2);   // = 130816
    CHECK(total == half * half);

    // ── ③ aarch64 FPU 浮点语义（非可精确表示小数的累加误差界）──
    // 32×32 全 0.1 矩阵自乘：C[0][0] = 32 × (0.1×0.1)，解析值 0.32；
    // 0.1 不可精确表示，64 次乘加后误差必须仍在 1e-12 内
    TNT::Array2D<double> A32(32, 32, 0.1);
    TNT::Array2D<double> C32 = TNT::matmult(A32, A32);
    CHECK(std::fabs(C32[0][0] - 0.32) < 1e-12);

    if (g_failures != 0) {
        std::cerr << "libtnt ohos: " << g_failures << " check(s) FAILED" << std::endl;
        return 1;
    }
    std::cout << "libtnt ohos: all 6 checks passed (musl clock path + heap pages + aarch64 FPU)" << std::endl;
    return 0;
}
