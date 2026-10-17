# lfortran-runtime 0.61.0 — 适配笔记

## 概述

| 项 | 值 |
|---|---|
| 上游 | https://github.com/lfortran/lfortran（tag v0.61.0） |
| 形态 | LFortran 的 C 运行时库 `liblfortran_runtime`（源码 `src/libasr/runtime/lfortran_intrinsics.c`，约 1 万行纯 C） |
| 依赖 | 无第三方 Conan 依赖；仅 libc/libm |
| 许可证 | BSD-3-Clause |
| 源 | GitHub 官方仓 tag 归档（R39）；sha256 `7bb5c609…d4ce` |
| sha256 双源核对 | 本地计算 == FreeBSD ports `lang/lfortran` distinfo @ commit 47e2bdf1ce28（"upgrade to v0.61.0"），均为 `7bb5c609dfff1aef3ef1c75c82fba9889da9949bc5055612e6f1d039f4f2d4ce`（4134363 B）；Homebrew homebrew-core 已无该 formula（404） |

## tarball 实测（以实际结构为准）

```
lfortran-0.61.0/
├── src/libasr/runtime/                   # ★ 本包范围：C 运行时库
│   ├── lfortran_intrinsics.c (345 KB)    #   _lfortran_* / _lcompilers_* 实现
│   ├── lfortran_intrinsics.h (23 KB)     #   头（含 LFORTRAN_API 导出声明）
│   ├── cuda_cpu_runtime.c/.h             #   可选 CUDA CPU 运行时（上游未被 SRC 引用）
├── src/runtime/
│   ├── legacy/CMakeLists.txt             #   上游构建 lfortran_runtime(.so) + lfortran_runtime_static(.a)
│   ├── pure|impure|openmp/*.f90          #   Fortran 侧运行时模块（需 LFortran 自举）
│   ├── tests/*.f90 (12 个)               #   上游运行时测试（Fortran，需 LFortran）
├── src/CMakeLists.txt                    #   第 8 行 add_subdirectory(runtime/legacy)
└── CMakeLists.txt                        #   顶层强依赖 LLVM/MLIR 全量工程
```

**关键结论**：本包交付的"运行时库"= `src/libasr/runtime/lfortran_intrinsics.c`。
上游由 `src/runtime/legacy/CMakeLists.txt` 构建为 `liblfortran_runtime.so`（SHARED，
VERSION 0.61.0 / SOVERSION 0）与 `liblfortran_runtime_static.a`（STATIC），安装头文件到
`include/lfortran/impure/`。

## 构建策略（为何不走上游 CMake）

- 上游**顶层** CMake 会编译整个编译器（libasr 前端 + parser + LLVM 后端），需 `find_package(LLVM)`
  与 re2c/bison/rapidjson 等，对"只交付运行时库"过重且不可行。
- 运行时库本身是**独立可编的单文件 C**：实测 `clang -O2 -fPIC -I<src>/src -c lfortran_intrinsics.c` 直接成功
  （rc=0），唯一前置是 `<libasr/config.h>`。
- `<libasr/config.h>` 上游由 `src/libasr/CMakeLists.txt` 的 `configure_file(config.h.in …)` 生成；
  其内容全是 `#cmakedefine`（默认全部关闭）+ 版本宏，且 `lfortran_intrinsics.c` **不引用任何可选特性宏**
  （仅以 `#ifdef HAVE_RUNTIME_STACKTRACE` 条件包围 stacktrace 段）。故配方在 `generate()` 中私有生成等价
  的最小 `libasr/config.h`（仅版本宏），不引入 CMake 全量工程。
- 因此配方 `build()` 直接调用 OHOS SDK clang 编译单文件，产出与上游**同名**的
  `liblfortran_runtime_static.a`（默认 shared=False）/ `liblfortran_runtime.so.0.61.0` + 软链
  （shared=True），与上游命名、安装布局一致。
- **范围裁剪**：上游 Fortran 侧运行时模块（`src/runtime/{pure,impure,openmp}/*.f90`，如
  `lfortran_intrinsic_iso_fortran_env.f90`）在 `src/runtime/CMakeLists.txt` 中以
  `CMAKE_Fortran_COMPILER=lfortran`（LFortran 自身）编译 → 需先自举出 LFortran 编译器；OHOS 无该编译器，
  故不在本包范围（本包只交付 C 运行时库，不含编译器前端）。裁剪证据：上游 `src/runtime/CMakeLists.txt`
  的 `project(lfortran_unif_runtime C Fortran)` 与 `lfortran_compile_runtime` 宏依赖 `$CMAKE_Fortran_COMPILER`。

## 关键适配点：musl 缺失 GNU 扩展 `feenableexcept`

**现象（实测）**：直接把 `lfortran_intrinsics.c` 交给 OHOS clang 编译，链接为 `-shared` 可过，但
`llvm-nm -D -u` 显示唯一的**非 libc/libm 未定义符号**是 `feenableexcept`；编译器同时给出
`warning: call to undeclared function 'feenableexcept'; ISO C99 and later do not support implicit function
declarations`（`lfortran_intrinsics.c:8524`）。

**根因**：`_lfortran_enable_fpe_traps()` 在 `#elif defined(__linux__)` 分支内调用 `feenableexcept(excepts)`。
`feenableexcept` 是 GNU/glibc 扩展，**musl（OHOS 使用的 libc）不提供**（sysroot `libc.so` 中仅有
`fegetexceptflag`，无 `feenableexcept`）。故：
- 编 `.so` 时因 `-shared` 默认允许未定义符号而"看似通过"，但运行期一旦走到该函数即符号解析失败；
- 编静态库并让消费者调用该符号时，链接期直接 `undefined reference to 'feenableexcept'`。

**修复（补丁 0001）**：在保留 glibc 路径的前提下追加非 glibc 回退——
`#if defined(__GLIBC__)` 走 `feenableexcept`，`#elif defined(__aarch64__)` 直接读写 ARMv8-A 的
**FPCR** trap-enable 位（8=IOE/9=DZE/10=OFE/11=UFE/12=IXE），`#else` 保持屏蔽。守卫用
`__GLIBC__`/`__aarch64__`（POSIX 语义，**非 OHOS 专有**，符合"源码修改四不"与 PF5），
与文件内既有 Apple/ARM64 分支同一手法。

**验证**：
- `git apply --check -p1` PASS（干净副本）。
- 打补丁后编译：`llvm-nm -D -u liblfortran_runtime.so` 中 `feenableexcept` 已消除（未定义符号 157 个，全部为 libc/libm 标准符号）。
- `test_package` 实机调用 `_lfortran_enable_fpe_traps(1)` 不崩溃，覆盖该补丁路径。

## 上游测试清点（R51 三步法）

| 项 | 结论 |
|---|---|
| 本包范围（C 运行时库）自带测试 | 无（src/libasr/runtime/ 下仅 .c/.h） |
| 上游运行时测试 | `src/runtime/tests/` 共 **12** 个 `.f90`（test_abs/test_bit/test_cos/test_hyperbolics/test_inverse_trig/test_iso_c_binding/test_iso_fortran_env/test_kind/test_sin/test_sin2/test_strings/test_tan） |
| 可运行性 | **不可运行**：由 `src/runtime/tests/CMakeLists.txt` 以 `CMAKE_Fortran_COMPILER=lfortran` 编译；需先自举出 LFortran 编译器二进制，OHOS 设备无该编译器（具体技术原因：缺 Fortran 前端编译器，非"没环境"） |
| 实测通过率 | 0/12（如实：未运行，附清点证据于 MANIFEST.yml） |
| test_package 补全 | 6 断言（见下），消费者链接级真实调用 API（R34） |

## 测试设计（test_package）

`test_lfortran_runtime.c`（C，链接 `liblfortran_runtime(_static)`）断言：
1. `_lfortran_dsin(0.0) == 0`
2. `_lfortran_dcos(0.0) == 1`
3. `_lfortran_sum(4, [1,2,3,4]) == 10`
4. `_lfortran_init_random_seed(42)` 后 `_lfortran_random() ∈ [0,1)`
5. `_lfortran_enable_fpe_traps(1)` 不崩溃（覆盖 musl 补丁路径）
6. 调用 fpe 设置后 `_lfortran_dsin` 仍正常

纯计算 + 标准输出，无文件/网络依赖（无头环境纪律）；断言失败返回非 0。

## 验证状态

- [x] tarball 结构实测（C 运行时库可独立编译）
- [x] sha256 双源核对（FreeBSD distinfo == 本地）
- [x] 补丁 `git apply --check` PASS + 编译后 `feenableexcept` 未定义符号消除
- [ ] `conan create` EXIT=0（本机）
- [ ] CI 双绿

## 踩坑记录

- `editFile` 类工具重写文件时会规范化整文件行尾空白，用它改源码生成补丁会引入数百行无关 diff；
  改用「字节精确 `str.replace` + `diff -u --label a/… --label b/…`」生成，得到单 hunk 干净补丁。
- 编译时 `-I` 指向源码根须为 `<src>/src`（`#include <libasr/runtime/lfortran_intrinsics.h>` 需
  `<src>/src/libasr/...` 可解析），`config.h` 另置于私有 include（`<inc>/libasr/config.h`）。
