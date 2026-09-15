# openblas64 0.3.34 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-12
- 编译器: clang/clang++（设备 hnp，/data/service/hnp/bin/clang）
- 状态: built
- 上游: https://github.com/OpenMathLib/OpenBLAS/releases/download/v0.3.34/OpenBLAS-0.3.34.tar.gz
- sha256: cd7e129868320cc2d033afa920e31202dfe0b8066a5b66661900ccc0f197dfed

## 定位
- OpenBLAS ILP64（64 位整型接口）变体：blasint/lapack_int 为 64 位，支持大数组索引。
- 与 LP64 包（openblas）并存：本包产 libopenblas64（SONAME libopenblas64.so.0），不与 libopenblas 冲突。
- 同源复用 openblas 0.3.33/0.3.34 经验（见 archives/o/openblas/0.3.33/notes.md 与 0.3.34/notes.md）。

## 编译步骤

设备原生（HarmonyOS PC 真机，os=OHOS arch=armv8）：

```bash
make TARGET=ARMV8 BINARY=64 INTERFACE64=1 LIBNAMESUFFIX=64 \
  HOSTCC="/data/service/hnp/bin/clang" CC="/data/service/hnp/bin/clang" \
  AR="/data/service/hnp/bin/llvm-ar" RANLIB="/data/service/hnp/bin/llvm-ranlib" \
  NOFORTRAN=1 NO_SHARED=0 NO_AFFINITY=1 shared
make TARGET=... INTERFACE64=1 LIBNAMESUFFIX=64 ... PREFIX=<package_folder> install
```

要点：
- `INTERFACE64=1` 开 ILP64 ABI（`USE64BITINT`/`LAPACK_ILP64`）；`LIBNAMESUFFIX=64` 得库名
  libopenblas64（不用 `SYMBOLSUFFIX=64_`，单包内符号保持上游默认，自洽且消费方 `-lopenblas64`）。
- `NOFORTRAN=1`（官方主变量，自动置 `C_LAPACK=1` f2c 版 LAPACK + LAPACKE），不依赖 Fortran 工具链。
- `package()` 走 `make install`（生成 openblas_config.h/lapack.h、加工 cblas.h、产出
  lib/pkgconfig/openblas64.pc 与 lib/cmake/openblas/），并手动补 LICENSE 三件套到 licenses/。
- `.so` 经 binary-sign-tool 自签（XPM dlopen 要求）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | blas_server.c 链接报 pthread_setaffinity_np 未定义 | OHOS musl 的 libc.so 不导出该符号（仅 libc.a 有），且该段不受 NO_AFFINITY 保护 | 通用能力探测：构建期真实编译+链接探测，失败则不定义 HAVE_PTHREAD_SETAFFINITY_NP，补丁将 affinity 代码由该宏门控（无平台宏） |
| 2 | ILP64 与 LP64 库名冲突 | 仅 INTERFACE64=1 不改库名，仍产 libopenblas | 加 LIBNAMESUFFIX=64，得 libopenblas64，与 openblas 包并存 |
| 3 | 测试整型 ABI | ILP64 下 blasint/lapack_int 为 64 位，plain int 传参在 AArch64 上高 32 位未定义 | test.c 一律用 blasint/lapack_int/int64_t；另断言 sizeof(lapack_int)==8 作 ILP64 硬证据 |

## 源码修改

- patches/0002-ohos-musl-affinity.patch（portability，与 openblas 0.3.33 同源）：
  driver/others/blas_server.c 的 affinity 段由 `#if defined(OS_LINUX) &&
  defined(HAVE_PTHREAD_SETAFFINITY_NP)` 门控，宏由构建期探测产生。

## 依赖版本

- 无运行时 requires（纯 C，无 Fortran 工具链依赖）。
- 构建工具：设备 hnp clang/llvm-ar/llvm-ranlib，SDK llvm/lib（LD_LIBRARY_PATH 给 lld 正确 libxml2）。

## 上游测试审计

- utest/：openblas_utest + openblas_utest_ext（纯 C，同源 0.3.33 实测 1650 项；0.3.34 以真机预检实测为准）。
- ctest/：12 个 CBLAS C 测试（xscblat/xdcblat/xccblat/xzcblat 各 1/2/3）。
- test/：14 个 Fortran BLAS 主程序——无 Fortran 编译器，未执行。
- lapack-netlib/：约 1243 项 Fortran——无 Fortran 编译器，未执行。
- 接入方式：conanfile.py `_run_upstream_tests()` 在 build 流程内真实构建+执行 utest/ctest；
  Fortran 缺编译器时如实跳过，不计入通过。

## 验证结果

```bash
conan create . --user=ohpcd --channel=stable（真机，待 HMBS 预检回填实测）
./test_probe（7 项断言，待真机预检回填）
```

- 证伪要求：参照任务守则，确认参照文件非空；必要时以 exit 1 桩验证 harness 能抓失败；
  区分通过与静默跳过（跳过计 skip，不计 pass）。

## 注意事项

- 消费方链接 `-lopenblas64`，头文件 cblas.h/lapack.h/lapacke.h 与 LP64 同名但整型宽度不同；
  同一进程内勿混用 LP64 与 ILP64 符号。
- Fortran LAPACK 测试恢复条件：OHOS Fortran 编译器可用后执行 make blas-test/make lapack-test。
