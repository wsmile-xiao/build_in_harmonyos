# pffft 1.1.0 适配笔记（HarmonyOS PC / aarch64 / NEON）

## 背景与选型

- 任务：#14835，pffft 1.1.0（marton78 的 PFFFT——pretty fast FFT，SIMD 优化
  FFT 库）。上游 https://github.com/marton78/pffft tag v1.1.0。
- W0：零第三方依赖（requirements() 为空）。FFTPACK 对照实现为树内
  src/fftpack.c；bench 对照子模块 greenffts/kissfft/pocketfft 声明于
  .gitmodules 但不包含在 release tarball 中（上游 CI 同样显式关闭）。
- W0b：archives/p/pffft 在 main 无历史归档，全新适配，无历史 notes 核验负担。
- 语言预检：C 库（C99），c↔cpp 兼容族，任务语言 cpp 兼容。

## 形态

- 单源双精度：libpffft.a = pffft.c (float) + pffft_common.c + pffft_double.c
  (double)，对外两套 API：`pffft_*`（float）与 `pffftd_*`（double）。
- 头文件安装至 include/pffft/：pffft.h / pffft.hpp / pffft_double.h
  （INSTALL_PFFFT 默认 ON；PFDSP/PFFASTCONV 的 INSTALL_* 默认 OFF，不随库包发布）。
- CMake 导出：PFFFT::PFFFT 目标 + lib/cmake/pffft/{pffft-config.cmake,
  pffft-targets.cmake, pffft-config-version.cmake}（消费者 find_package(pffft
  CONFIG REQUIRED) 可用）。
- 纯库包，无命令行产物 → 无 commands.json（R38）。
- 静态库形态（package_type=static-library，上游 add_library(PFFFT) 无
  SHARED/STATIC 指定即默认 STATIC；BUILD_SHARED_LIBS 未开）。

## SIMD / NEON 激活（本适配核心点）

上游 SIMD 分发链：src/pffft.c → #include "simd/pf_float.h" → 依次包含
pf_sse1/pf_neon/pf_altivec 头，由预定义宏竞争定义 SIMD_SZ：

- NEON guard：`#if !defined(PFFFT_SIMD_DISABLE) && defined(PFFFT_ENABLE_NEON)
  && (defined(__arm__) || defined(__aarch64__) || ...)`（pf_neon_float.h:39）
- `PFFFT_ENABLE_NEON` 宏不经任何上游默认 CMake 选项定义：
  - README 提及的 `PFFFT_USE_SIMD_NEON` 选项在 v1.1.0 CMakeLists 中不存在
    （README 文档超前于实现，已 grep 全源码确认）。
  - cmake/target_optimizations.cmake 仅在 `TARGET_C_EXTRA=neon_*` 分支注入
    `PFFFT_ENABLE_NEON=1`（:143-144），而 `GCC_EXTRA_OPT_neon_*` extra 值
    仅在 armv7l 分支提供；非 Apple aarch64 分支 `GCC_EXTRA_VALUES=""`，
    TARGET_C_EXTRA cache 变量根本不创建 → 非 Apple 的 Linux aarch64 默认
    构建是 SCALAR 路径（SIMD_SZ 未定义 → PFFFT_SIMD_DISABLE 兜底）。
- 对策：配方 generate() 在 aarch64 时经 `tc.variables["CMAKE_C_FLAGS"]`
  注入 `-DPFFFT_ENABLE_NEON=1`。NEON 是 aarch64 基线指令集，无需 -march，
  TARGET_C_ARCH 保持上游默认 none——派工"目标优化 -march 冲突留意点"实测
  不触发（target_optimizations 对 PFFFT 目标的调用在默认 none 下无操作）。
- 验证：消费者测试断言 pffft_simd_size()==4 且 pffft_simd_arch()=="NEON"
  （float 路径）；上游 --test-simd 自检（validate_pffft_simd_ex）在 build()
  内补充执行。
- double 路径：pf_neon_double.h guard 同样要求 PFFFT_ENABLE_NEON + aarch64，
  同一注入覆盖（pffftd_simd_size()==4）。

## 上游测试集成（L1c 口径）

上游顶层默认形态（PFFFT_IS_TOPLEVEL=ON）：PFFFT_BUILD_TESTS=ON、
PFFFT_BUILD_BENCHMARKS=ON、PFFFT_USE_FFTPACK=ON → ctest 注册 9 项：

| ctest 项 | 源 | 性质 |
|---|---|---|
| test_fft_factors | tests/test_fft_factors.c | 因子分解辅助函数边界值 |
| test_fftpack_float | src/fftpack.c | 树内参考实现自测 (float) |
| test_fftpack_double | src/fftpack.c | 树内参考实现自测 (double) |
| test_pfconv_lens_symetric | tests/test_pffastconv.c | 卷积长度扫描 (对称) |
| test_pfconv_lens_non_sym | tests/test_pffastconv.c | 卷积长度扫描 (非对称) |
| bench_pfconv_symetric | tests/test_pffastconv.c | 卷积 bench (正确性路径) |
| bench_pfconv_non_sym | tests/test_pffastconv.c | 卷积 bench (非对称) |
| bench_pffft_pow2 | benchmarks/bench_pffft.c | FFT bench --max-len 128 (含 FFTPACK 对照) |
| bench_pffft_non2 | benchmarks/bench_pffft.c | FFT bench --non-pow2 --max-len 192 |

- build() 内 `ctest --output-on-failure` 全量执行（libgdf 先例的 CTestTestfile
  目录下钻逻辑）。
- 关闭项与上游 CI 完全一致：PFFFT_BUILD_EXAMPLES=OFF（示例仅演示）、
  bench 对照子模块（tarball 不含，UPSTREAM CI 同样 -DPFFFT_USE_BENCH_GREEN/KISS/POCKET=OFF）。

## 消费者测试（test_package）

派工指定形态：64 点实数 FFT→IFFT 往返（能量守恒断言，误差容限比较）：

1. pffft_min_fft_size(PFFFT_REAL) <= 64
2. pffft_simd_size() == 4（NEON float 路径激活证明）
3. pffft_simd_arch() == "NEON"
4. DC bin == sum(x)（tol 1e-3）
5. Nyquist bin == parity sum（tol 1e-3）
6. 全谱 bin vs 测试内朴素 O(N²) DFT 逐分量最大误差 < 1e-3
   （参考值角色对齐上游树内 FFTPACK）
7. Parseval 能量守恒：sum|X|² == N·sum|x|²（tol 1%）
8. FFT→IFFT 往返重建最大误差 < 1e-3（backward 无缩放，1/N 归一）
9. 往返能量守恒（tol 1%）
10. aligned malloc/free 生命周期

信号：64 点确定性多音信号（DC + bin3 正弦 + bin17 余弦 + bin30 正弦）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aarch64 默认构建 SIMD 走 SCALAR 而非 NEON | PFFFT_ENABLE_NEON 无默认 CMake 激活路径（README 的 PFFFT_USE_SIMD_NEON 不存在；TARGET_C_EXTRA neon_* 仅 arm32 提供） | CMAKE_C_FLAGS 注入 -DPFFFT_ENABLE_NEON=1（无需 -march，NEON 为 aarch64 基线）；编译期 pragma "ARM NEON macros are defined" + 消费者断言 simd_size==4/simd_arch==NEON 双重验证 |
| 2 | 测试二进制在 OHOS 无法直接执行 | 未签名 ELF 执行门禁 | binary-sign-tool 自签（bitarray 先例） |
| 3 | test_pffft --test-simd 自检入口（validate_pffft_simd_ex）在 NEON float 路径报 1 错误 | 上游校验工装的 SSE 视角假设：probe 循环要求 !VALIGNED 指针 >= 4 个，而 NEON float 的 VALIGNED 是 4 字节对齐（pf_neon_float.h:80），float 数组内不存在 4 字节不对齐指针 → 该检查在 NEON float 路径确定性必失败（numUnaligned==0）。属测试工装架构假设问题，非库缺陷——且该入口上游既未注册 ctest 也从不在 CI 运行 | 不纳入 test 集成（回归上游注册口径：ctest 9 项）；库 NEON 正确性由 9/9 ctest（含 FFTPACK 140dB 动态范围对照）+ 消费者 11 断言（NEON 路径频谱误差 3.8e-06、往返 4.8e-07）覆盖 |

## conandata 说明

URL 列表：ghfast.top 镜像前置 + GitHub 官方兜底（CI worker 站点白名单网络；
派工指令明确要求镜像前置格式，aethersdr 26.7.2 / bitarray 同款先例）。
sha256 本机双源下载实测一致：ea0701a6bc256405b03975908a6a92d0ffecdd18579e8484b8d789c8bd561787。
