# openblas 0.3.28 编译笔记（HarmonyOS PC · Makefile + flang）

## 定位

OpenBLAS 0.3.28 —— BLAS/LAPACK 实现。**设备原生** recipe：在鸿蒙 PC 真机
`conan create`，用 `tool_requires` 的 `flang-ohos/20.1.0` 提供 Fortran 编译器编 LAPACK。

选 0.3.28 这个版本的直接动因：**PyPI 上 cvxopt 1.3.3 的 aarch64 wheel 内嵌的正是
`libopenblas_armv8p-r0.3.28.so`**。本配方按上游 Makefile 构建，产出的库实名与之逐字一致，
从源码编 cvxopt / 或按名对齐时都省事。

## 与本仓此前 0.3.28 配方的差异（这是重做的原因）

此前制品仓里的 `openblas/0.3.28`（rrev `36036dfd…`）是 **cmake + `NOFORTRAN=ON` +
`C_LAPACK=ON`** 构建的，即 LAPACK 用的是 f2c 翻译版而非真 Fortran。实测差距
（符号数均用 `nm -D … | grep ' T '` 同口径测量）：

| | 旧配方（cmake + C_LAPACK） | 本配方（make + flang） |
|---|---|---|
| 导出函数符号 | **6353** | **7514**（+1161） |
| 静态库 | ❌ 无 | ✅ `libopenblas_armv8p-r0.3.28.a` |
| 版本软链 | ❌ 无 | ✅ `libopenblas.so` / `.so.0` → 实名 |
| 库实名 | `libopenblas.so`（非规范） | `libopenblas_armv8p-r0.3.28.so`（上游规范） |
| SONAME | `libopenblas.so`（无版本） | `libopenblas.so.0` |

旧配方之所以不出版本软链，是因为它显式传了：

```python
defs.append("-DCMAKE_PLATFORM_NO_VERSIONED_SONAME=ON")
# 注释称：鸿蒙 HMDFS 不支持建符号链接
```

**该前提经实测不成立**——同一台设备、同一个 conan cache 目录下，本仓的 ffmpeg、poppler
25.12.0.1、以及 openblas 0.3.34 都正常建出了两级版本软链（`ls -l` 可见 `lrwxrwxrwx`）。
这个 workaround 属误诊，代价是 SONAME 不合社区惯例（上游是 `libopenblas.so.0`），
任何按 `libopenblas.so.0` 查找的消费方都会落空。

## 构建方式

与本仓 `0.3.33` / `0.3.34` 同法（用户选定的 B 方案）：

- `make TARGET=ARMV8 BINARY=64 F_COMPILER=FLANGNEW NOFORTRAN=0 shared`
- C 编译/链接用设备 hnp clang（`/data/service/hnp/bin/clang`）
- Fortran 用 `tool_requires` 的 `flang-ohos/20.1.0`
- `FEXTRALIB` 带上 flang 的 `libFortranRuntime.a` + `libFortranDecimal.a` + `-lm`

## 补丁（2 个，均为 0.3.28 专属、非从 0.3.34 照搬）

### 0001 — `exports/Makefile` 补 FLANGNEW 共享库链接分支

0.3.28 的 `f_check` 与 `Makefile.system` **已支持 FLANGNEW**（`f_check:113`：flang 主版本
≥17 即判为 FLANGNEW，flang-ohos 是 20.1.0，命中），但 `exports/Makefile` 的 `.so` 链接规则
里**只有 `FLANG` 分支、没有 `FLANGNEW`**（0.3.29+ 上游才补上）。

于是 FLANGNEW 落到通用 `else` 分支——那里已经用 `$(CC)` 链接（正是所需，不能用 `$(FC)`，
否则 flang 当链接器会塞入 host 的 libLTO/libunwind），但**不带 `$(FEXTRALIB)`**，
flang 运行时链不进 `.so`，结果是一堆 `_FortranA*` 未定义符号。

本补丁补一个显式的 `FLANGNEW` 分支，结构与 0.3.29+ 上游一致。

> 注：0.3.34 的同名补丁是**修改**既有 FLANGNEW 分支（`$(FC)`→`$(CC)` 并加 `$(FEXTRALIB)`），
> 与本补丁的形态不同——0.3.28 里那个分支根本不存在。两版补丁不可互换。

### 0002 — `driver/others/blas_server.c` 的 affinity 加 `__OHOS__` 守卫

OHOS musl 的 `libc.so` 不导出 `pthread_setaffinity_np`（仅 `libc.a` 有），
而 `openblas_setaffinity` / `getaffinity` 在 `#ifdef OS_LINUX` 下无条件编入，
`NO_AFFINITY` 挡不住它俩。加 `!defined(__OHOS__)` 守卫。

## 验证

test_package **直接编译链接**（非 dlopen）并做**真实数值计算**，6 条断言：

| 断言 | 覆盖 |
|---|---|
| `cblas_ddot` 点积 = 70 | BLAS C 接口 |
| `cblas_dgemm` 矩阵乘 = [19 22; 43 50] | BLAS C 接口 |
| `dgesv_` 解 Ax=b → x=[0.8, 1.4] | LAPACK Fortran |
| `dpotrf_` Cholesky → L=[2 0; 1 2] | LAPACK Fortran |
| `dgeev_` 非对称特征值 = {2, 3} | LAPACK Fortran（重量级路径） |
| `openblas_get_config()` 含 `0.3.28` | 版本一致性 |

**为什么重点压 LAPACK**：本次改动的核心就是把 f2c 版 LAPACK 换成真 Fortran，
`dgeev_` 会走到大量 Fortran 代码路径，是该改动是否真正生效的硬证据——
仅解析符号（`dlsym`）证明不了这一点。

## 已知限制

- `TARGET=ARMV8` 是 AArch64 通用基线，未针对具体核心调优、也未开 `DYNAMIC_ARCH`。
  若目标机型固定，改 `blas_target` option 为 `NEOVERSEN1` / `CORTEXA76` 等可提升性能；
  要通吃多机型则需 `DYNAMIC_ARCH=1`（体积显著增大，运行时分发）。
- **LP64 接口**（32 位整数），非 ILP64。`dgemm_` 有、`dgemm_64_` 无。
  cvxopt / 多数科学计算库用的正是 LP64；numpy 2.x 走 ILP64，需另出 `INTERFACE64=1` 变体。
- 线程模型为 **pthread**（非 OpenMP），故库实名带 `p` 后缀。

## 状态

built（真机 `conan create -pr ohos-native` + test_package 全绿）
