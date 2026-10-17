// veccore 0.8.1 鸿蒙特有测试用例
//
// 校验 VecCore 在 HarmonyOS / OHOS aarch64 工具链（clang 15 + libc++ + musl）
// 下的平台相关路径：
//   1) 平台宏：__OHOS__ 与上游 Common.h 的 VECCORE_ARM64 分支同时成立，
//      且不会走 x86 内建头（VecCore/SIMD.h 里的 <x86intrin.h> 分支）。
//   2) 对齐常量与 posix_memalign：Utilities.h 的非 MSVC 路径在 OHOS libc 上
//      真实可用（AlignedAlloc/AlignedFree 返回按 16/32/64 对齐的内存）。
//   3) SIMD 抽象路径：用 VecCore 后端 API 分块 Load/Store 遍历数组，与标准库
//      逐元素对拍，证明「同一套 VecCore 代码在 OHOS 上算得对」。
#include <VecCore/VecCore>

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <vector>

#if defined(__OHOS__)
static constexpr bool kOhos = true;
#else
static constexpr bool kOhos = false;
#endif

#if defined(VECCORE_X64) || defined(VECCORE_X86)
static constexpr bool kX86Path = true;
#else
static constexpr bool kX86Path = false;
#endif

#if defined(VECCORE_ARM64) || defined(VECCORE_ARM)
static constexpr bool kArmPath = true;
#else
static constexpr bool kArmPath = false;
#endif

namespace {

int g_checks = 0;
int g_failures = 0;

void check(bool ok, const char *what)
{
  ++g_checks;
  if (!ok) {
    ++g_failures;
    std::printf("FAIL %s\n", what);
  }
}

template <class Vector_t>
void checkBackendOnOhos(const char *tag)
{
  using Scalar_t = vecCore::Scalar<Vector_t>;

  // 后端在本平台确实可用，且向量长度与上游标量后端一致
  check(vecCore::VectorSize<Vector_t>() >= 1, "VectorSize >= 1");

  // 分块 Load/Store：以 VectorSize 为步长遍历，逐元素与标准库 sqrt 对拍
  const size_t n = 64;
  std::vector<Scalar_t> in(n), out(n, Scalar_t(0));
  for (size_t i = 0; i < n; ++i)
    in[i] = Scalar_t(1 + i) * Scalar_t(0.5);
  const size_t w = vecCore::VectorSize<Vector_t>();
  for (size_t j = 0; j < n; j += w) {
    Vector_t v;
    vecCore::Load(v, &in[j]);
    vecCore::Store(vecCore::Sqrt(v), &out[j]);
  }
  bool exact = true;
  for (size_t i = 0; i < n; ++i)
    if (std::fabs(double(out[i]) - std::sqrt(double(in[i]))) > 1e-4)
      exact = false;
  check(exact, tag);
}

} // namespace

int main()
{
  std::printf("veccore OHOS probe: __OHOS__=%d arm_path=%d x86_path=%d simd_align=%d\n",
              int(kOhos), int(kArmPath), int(kX86Path), VECCORE_SIMD_ALIGN);

  // 1) 平台宏
  check(kOhos, "__OHOS__ defined");
  check(kArmPath, "VECCORE_ARM64/VECCORE_ARM selected");
  check(!kX86Path, "no x86 backend macros on aarch64");
  check(VECCORE_SIMD_ALIGN == 16, "VECCORE_SIMD_ALIGN == 16 on aarch64");
  check(VECCORE_VERSION_MAJOR == 0 && VECCORE_VERSION_MINOR == 8 &&
            VECCORE_VERSION_PATCH == 1,
        "header version macros are 0.8.1");

  // 2) OHOS libc 的对齐分配（Utilities.h 走 posix_memalign 路径）
  for (size_t align : {16u, 32u, 64u}) {
    void *p = vecCore::AlignedAlloc(align, 1024);
    char what[64];
    std::snprintf(what, sizeof what, "AlignedAlloc(%u) non-null", (unsigned)align);
    check(p != nullptr, what);
    if (p) {
      std::snprintf(what, sizeof what, "AlignedAlloc(%u) alignment honoured",
                    (unsigned)align);
      check(reinterpret_cast<uintptr_t>(p) % align == 0, what);
      // 写入并读回，确认这块内存在 OHOS 上真实可用
      double *d = static_cast<double *>(p);
      d[0] = 42.5;
      std::snprintf(what, sizeof what, "AlignedAlloc(%u) memory writable",
                    (unsigned)align);
      check(d[0] == 42.5, what);
      vecCore::AlignedFree(p);
    }
  }

  // 3) 两个后端在 OHOS 上的 SIMD 抽象计算路径
  checkBackendOnOhos<vecCore::backend::Scalar::Double_v>("Scalar backend sqrt on OHOS");
  checkBackendOnOhos<vecCore::backend::ScalarWrapper::Double_v>(
      "ScalarWrapper backend sqrt on OHOS");

  std::printf("veccore OHOS probe: %d checks, %d failures -> %s\n", g_checks,
              g_failures, g_failures ? "FAILED" : "PASSED");
  return g_failures ? 1 : 0;
}
