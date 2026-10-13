/* HarmonyOS PC（OHOS aarch64）专项测试。
 *
 * 与通用 test.c（I*B==B、rank(I3)=3）互补，本文件验证三件事：
 *   1) 交叉编译目标属性：__OHOS__/__aarch64__/小端/字长——这些是
 *      m4ri「word=uint64_t + 位打包」正确性在 OHOS 上的前提；
 *      （musl 的验证不靠 __MUSL__ 宏——OHOS Clang+musl 目标不保证预定义它，
 *      属不可靠测试——改由 conanfile.py 对本测试产出的 ELF 做真实检查：
 *      ELF64/EM_AARCH64/PT_INTERP=/lib/ld-musl-aarch64.so.1/无 GLIBC_* 依赖。）
 *   2) configure 探测结果与 AArch64 目标自洽：SSE2 必须为 0（x86 SIMD 在
 *      AArch64 上编不过也跑不了；若非 0，说明交叉探测串台到构建机）；
 *      cache 探测在 OHOS 上拿不到 /sys 与 hw.* 键 → 全 0，属安全退化，
 *      只打印不断言（下游以 mul/rank 的正确性来验证退化路径可用）；
 *   3) 核心 API 真实运行：跨 64 位字边界（70 列 > m4ri_radix=64）的
 *      mul / echelonize(rank) / transpose / add 与 PNG 文件往返。
 *      随机矩阵经 srandom(42) 固定种子，全部断言在数学上可手推。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <m4ri/m4ri.h>

static int failures = 0;

#define CHECK(cond, msg)                                                       \
  do {                                                                         \
    if (cond) {                                                                \
      printf("PASS: %s\n", msg);                                               \
    } else {                                                                   \
      fprintf(stderr, "FAIL: %s\n", msg);                                      \
      failures++;                                                              \
    }                                                                          \
  } while (0)

int main(void) {
  /* ---------- 1. OHOS AArch64 目标属性 ---------- */
#if defined(__OHOS__) || defined(__OHOS_FAMILY__)
  CHECK(1, "OHOS 目标宏存在 (__OHOS__/__OHOS_FAMILY__)");
#else
  CHECK(0, "OHOS 目标宏存在 (__OHOS__/__OHOS_FAMILY__)");
#endif
/* musl 运行时的验证**不在**这里做：OHOS Clang + musl 目标不保证预定义
 * __MUSL__，断言它存在是 CI #65698 唯一失败项、属不可靠测试。
 * 改由 conanfile.py 对最终链接出的 test_ohos ELF 做真实检查：
 * PT_INTERP == /lib/ld-musl-aarch64.so.1 且不依赖任何 GLIBC_* 版本符号。 */
#if defined(__aarch64__)
  CHECK(1, "AArch64 架构宏存在 (__aarch64__)");
#else
  CHECK(0, "AArch64 架构宏存在 (__aarch64__)");
#endif
  /* AArch64 OHOS 为小端；m4ri 的位打包（__M4RI_LEFT_BITMASK 等）按
   * 「最高位在字的最左侧」定义，端序错了读出的每一位都是反的。 */
#if defined(__BYTE_ORDER__) && defined(__ORDER_LITTLE_ENDIAN__)
  CHECK(__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__, "目标为小端 (__BYTE_ORDER__)");
#else
  {
    union { uint16_t u; unsigned char b[2]; } e = {1};
    CHECK(e.b[0] == 1, "目标为小端 (运行时探测)");
  }
#endif
  /* 字长：m4ri 在 64 位平台上 word=uint64_t、m4ri_radix=64。 */
  CHECK(sizeof(word) == 8 && m4ri_radix == 64, "word=8字节 且 m4ri_radix=64");

  /* ---------- 2. configure 探测与交叉目标自洽 ---------- */
#if __M4RI_HAVE_SSE2
  CHECK(0, "AArch64 目标上 SSE2 应为 0（x86 SIMD 探测串台）");
#else
  CHECK(1, "SSE2 按 AArch64 目标正确禁用 (__M4RI_HAVE_SSE2==0)");
#endif
  CHECK(__M4RI_HAVE_LIBPNG == 1, "libpng 支持已启用 (__M4RI_HAVE_LIBPNG==1)");
  /* configure 探测在 OHOS 上拿不到 /sys/devices/system/cpu 与 hw.* 键 →
   * m4ri_config.h 全 0；misc.h:569-599 在编译期把 0 回退为标准值
   * (16K/256K/4M)，打印的是回退后的生效值，不是 configure 原始探测值。 */
  printf("info: __M4RI_CPU_L1/L2/L3_CACHE 生效值 = %d/%d/%d (configure 探测 0 → misc.h 编译期回退)\n",
         (int)__M4RI_CPU_L1_CACHE, (int)__M4RI_CPU_L2_CACHE, (int)__M4RI_CPU_L3_CACHE);

  /* ---------- 3. 核心 API 真实运行（70 列，跨 64 位字边界） ---------- */
  const rci_t N = 70; /* > m4ri_radix：位打包至少跨 2 个 word */
  mzd_t *I = mzd_init(N, N);
  for (rci_t i = 0; i < N; i++) mzd_write_bit(I, i, i, 1);

  srandom(42);
  mzd_t *A = mzd_init(N, N);
  mzd_randomize(A);

  /* 3.1 单位阵乘任意矩阵：I*A == A（单位阵性质，逐行可手推） */
  mzd_t *C = mzd_mul(NULL, I, A, 0);
  CHECK(C != NULL && mzd_equal(C, A), "mzd_mul: I70*A == A（70x70，跨字边界）");

  /* 3.2 秩：单位阵满秩 N；把第 1 行清成第 0 行后秩必为 N-1 */
  mzd_t *D = mzd_copy(NULL, I);
  rci_t r_full = mzd_echelonize(D, 1);
  CHECK(r_full == N, "mzd_echelonize: rank(I70) == 70");
  for (rci_t j = 0; j < N; j++) mzd_write_bit(D, 1, j, mzd_read_bit(D, 0, j));
  /* D 此时是「已化简的单位阵 + 重复行」，重算秩 */
  mzd_t *D2 = mzd_copy(NULL, D);
  rci_t r_def = mzd_echelonize(D2, 1);
  CHECK(r_def == N - 1, "mzd_echelonize: 重复一行后 rank == 69");

  /* 3.3 转置对合：(A^T)^T == A。注意 mzd_transpose 内核用 RESTRICT 限定
   * dst/src，不支持 DST==A 就地转置（上游契约：DST 须为独立矩阵），
   * 故分两步各转一次，验证的是转置算子本身的对合性。 */
  mzd_t *T = mzd_transpose(NULL, A);
  mzd_t *T2 = mzd_transpose(NULL, T);
  CHECK(mzd_equal(T2, A), "mzd_transpose: (A^T)^T == A");

  /* 3.4 GF(2) 加法自逆：A + A == 0 */
  mzd_t *Z = mzd_add(NULL, A, A);
  int zero = 1;
  for (rci_t i = 0; i < N && zero; i++)
    for (rci_t j = 0; j < N && zero; j++)
      if (mzd_read_bit(Z, i, j)) zero = 0;
  CHECK(zero, "mzd_add: A+A == 0（GF(2) 自逆）");

  /* 3.5 PNG 文件往返：写出去、读回来，逐位相等。
   * 用文件路径而非 tmpfile()——OHOS musl tmpfile() 恒 EACCES 是已知平台差异
   * （上游 test_misc 由构建期 LD_PRELOAD shim 解决，包消费方不受影响）。 */
  const char *png = "test_ohos_roundtrip.png";
  int w = mzd_to_png(A, png, 9, "ohos-test", 0);
  mzd_t *R = (w == 0) ? mzd_from_png(png, 0) : NULL;
  CHECK(w == 0 && R != NULL && mzd_equal(R, A), "mzd_to_png/mzd_from_png: 70x70 文件往返逐位相等");
  remove(png);

  mzd_free(I); mzd_free(A); mzd_free(C); mzd_free(D); mzd_free(D2);
  mzd_free(T); mzd_free(T2); mzd_free(Z);
  if (R) mzd_free(R);

  if (failures) {
    fprintf(stderr, "test_ohos: %d 项失败\n", failures);
    return 1;
  }
  printf("test_ohos: HarmonyOS PC 专项测试全部通过\n");
  return 0;
}
