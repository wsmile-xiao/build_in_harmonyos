// vdt 0.4.4 HarmonyOS 专项测试用例
//
// R6 实质逻辑：OHOS 平台校验平台宏并验证 vdt 的 NEON 向量化路径与数组签名
// 符号在 OHOS 工具链下实际可用；非 OHOS 平台同样执行相同的 vdt 调用验证
// 路径（保证任一平台构建都能真正运行而非空壳）。
#include <vdt/vdtMath.h>

#include <cmath>
#include <cstdio>

#if defined(__OHOS__)
static constexpr bool kOnOhos = true;
#else
static constexpr bool kOnOhos = false;
#endif

#if defined(__ARM_NEON) || defined(__ARM_NEON__) || defined(__aarch64__)
static constexpr bool kNeonPath = true;
#else
static constexpr bool kNeonPath = false;
#endif

int main() {
  std::printf("vdt OHOS special test: kOnOhos=%d kNeonPath=%d\n",
              static_cast<int>(kOnOhos), static_cast<int>(kNeonPath));

  // NEON 向量化路径：数组签名符号来自 libvdt.so 导出（vdtMath_signatures.cc）
  const unsigned int n = 8;
  const double in[n] = {0.1, 0.5, 1.0, 2.0, -0.3, 3.5, 0.75, -1.25};
  double expOut[n];
  double out[n];
  vdt::expv(n, in, expOut);
  for (unsigned int i = 0; i < n; ++i) {
    double want = std::exp(in[i]);
    double rel = std::fabs((expOut[i] - want) / (want != 0.0 ? std::fabs(want) : 1.0));
    if (rel > 1e-7 || !std::isfinite(expOut[i])) {
      std::printf("FAIL expv[%u]: got=%.17g want=%.17g rel=%.3e\n", i, expOut[i], want, rel);
      return 1;
    }
  }
  vdt::sinv(n, in, out);

  // 逐项与标准库对拍，验证 OHOS 上 vdt 数值正确
  for (unsigned int i = 0; i < n; ++i) {
    double want = std::sin(in[i]);
    double rel = std::fabs((out[i] - want) / (want != 0.0 ? std::fabs(want) : 1.0));
    if (rel > 1e-7 || !std::isfinite(out[i])) {
      std::printf("FAIL sinv[%u]: got=%.17g want=%.17g rel=%.3e\n", i, out[i], want, rel);
      return 1;
    }
  }

  // 标量快速路径（头文件内联）
  const double e = vdt::fast_exp(1.0);
  if (std::fabs(e - std::exp(1.0)) > 1e-9) {
    std::printf("FAIL fast_exp(1.0): got=%.17g\n", e);
    return 1;
  }

  std::printf("vdt OHOS special test: PASSED\n");
  return 0;
}
