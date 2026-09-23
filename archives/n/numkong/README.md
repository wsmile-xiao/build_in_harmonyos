# numkong

NumKong 是可移植混合精度数学/线性代数/检索库，提供 2000+ SIMD 内核
（x86 AVX/AMX、Arm NEON/SVE/SME、RISC-V RVV、LoongArch LASX、Power VSX、
WASM SIMD128），覆盖点积、欧氏/角距离、批处理 GEMM 风格运算、地理空间
距离、稀疏交集、MaxSim 检索等。header-heavy C 库（246 头文件）+ 动态
分发库（libnumkong.so）。不依赖 numpy 本体（python/ 目录仅为绑定源码，
不在本包构建范围）。

## HarmonyOS 适配

- 上游仓库：https://github.com/ashvardanian/NumKong
- 版本：7.8.1
- 许可证：Apache-2.0
- Conan 引用：`numkong/7.8.1`
- 适配路径：路径 A（基础适配）
- 依赖：无（零 conan 依赖）

aarch64 NEON 路径适配要点：OHOS clang 15.0.4 忽略上游 NEON/SVE 内核的
per-function `__attribute__((target(...)))`（需 Clang 16+），配方通过
CMake cache 预填 ISA 探针结果锁定 armv8-a 基线 NEON 内核集；运行时
`nk_capabilities()` 动态分发保持完整。SVE/SVE2/SME 系列内核在 clang 15
下不可用，与上游编译器支持矩阵一致。

## 测试

上游双路径测试套全部通过（设备真实运行）：
- `nk_test`（header-only 内联内核）：485/485（26 断言组 + 459 内核精度行）
- `nk_shared_test`（动态分发库路径）：317/317（26 断言组 + 291 内核精度行）

详细测试统计见 [7.8.1/reports/test-report.md](7.8.1/reports/test-report.md) 和
[7.8.1/test_package/MANIFEST.yml](7.8.1/test_package/MANIFEST.yml)。

## 版本索引

- 7.8.1 — 首次适配（2026-09-03）
