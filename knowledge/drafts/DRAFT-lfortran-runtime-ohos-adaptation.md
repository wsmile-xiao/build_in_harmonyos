# DRAFT-lfortran-runtime-ohos-adaptation（草稿）: LLVM 系编译器运行时库的 musl 扩展符号缺失与组件切分

> 事件族：编译器/语言运行时库在 OHOS(musl) 上的构建与符号可移植性。
> 本条为 draft，编号由知识库主编确认，禁止直接 promote。

## 基本信息
- **严重度**: 2
- **类别**: toolchain, fortran, portability, runtime
- **principles**: P-TOOLCHAIN-001
- **similar_to**: E109（OHOS 无 Fortran 编译器）、E242（Fortran .mod 编译器私有 ABI）、E6339（flang-ohos 工具链用法）
- **作者**: Hawkninja21
- **来源**: lfortran-runtime 0.61.0 适配（run lfortran-runtime-0.61.0，2026-09-20）

## 错误特征（本库实测）

原始编译告警（file#L 定位）：
```
src/libasr/runtime/lfortran_intrinsics.c:8524:9: warning: call to undeclared function 'feenableexcept';
      ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
        feenableexcept(excepts);
        ^
```

链接/加载层面的真实后果（`llvm-nm -D -u` / 未定义符号核对）：
```
                 U feenableexcept          ← liblfortran_runtime 在 OHOS 上唯一的非 libc/libm 未定义符号
```
- `clang -shared` 因默认允许未定义符号而"看似通过"，但运行期一调用 `_lfortran_enable_fpe_traps` 即符号解析失败；
- 静态库被消费者调用该符号时链接期直接 `undefined reference to 'feenableexcept'`。

## 根因分析

1. `_lfortran_enable_fpe_traps()` 在 `#elif defined(__linux__)` 分支调用 `feenableexcept(excepts)`
   （`lfortran_intrinsics.c:8524`）。`feenableexcept` 是 **GNU/glibc 扩展**，**musl（OHOS 使用的 libc）不提供**：
   OHOS SDK sysroot 的 `libc.so` 仅导出 `fegetexceptflag`，无 `feenableexcept`。
   → 子模式 A：**非 glibc libc 缺失 glibc 专属扩展符号**。

2. LFortran 的"运行时库"是 C 运行时（`src/libasr/runtime/lfortran_intrinsics.c`），可独立编译；
   而上游顶层 CMake 强依赖 LLVM/MLIR 编译**编译器主体**，Fortran 侧运行时模块
   （`src/runtime/{pure,impure,openmp}/*.f90`）需 `CMAKE_Fortran_COMPILER=lfortran` **自举**。
   → 子模式 B：**编译器+运行时整体工程在 OHOS 上的组件切分**（只交付可独立编译的 C 运行时；
   私有生成上游由 CMake `configure_file` 产出的 `libasr/config.h`）。

## 修复模式（可跨库复用）

**子模式 A — FPCR 直写替代（保留 glibc 路径，守卫用 POSIX 语义）**：
```c
    if (excepts) {
#if defined(__GLIBC__)
        feenableexcept(excepts);
#elif defined(__aarch64__)
        // musl 等非 glibc libc 无 feenableexcept：按 ARMv8-A FPCR trap 位直写
        // 8=IOE 9=DZE 10=OFE 11=UFE 12=IXE
        uint64_t fpcr;
        __asm__ __volatile__("mrs %0, fpcr" : "=r"(fpcr));
        if (excepts & FE_INVALID)   fpcr |= (1ULL << 8);
        if (excepts & FE_DIVBYZERO) fpcr |= (1ULL << 9);
        if (excepts & FE_OVERFLOW)  fpcr |= (1ULL << 10);
        if (excepts & FE_UNDERFLOW) fpcr |= (1ULL << 11);
        if (excepts & FE_INEXACT)   fpcr |= (1ULL << 12);
        __asm__ __volatile__("msr fpcr, %0" : : "r"(fpcr));
#else
        (void)excepts;
#endif
    }
```
> 要点：守卫用 `__GLIBC__`/`__aarch64__`（**非 OHOS 专有**，符合 R8 "源码修改四不"），
> 与该文件内既有 Apple/ARM64 分支同风格，不引入空壳 stub。

**子模式 B — 组件切分构建**：不采用上游顶层 CMake；直接 `clang -O2 -fPIC` 编译运行时源文件，
私有生成 `libasr/config.h`（等价于上游 `configure_file` 全特性关闭时的产物），产出与上游**同名**的
`liblfortran_runtime_static.a` / `liblfortran_runtime.so.*` 与头文件 `include/lfortran/impure/`。

## 验证证据（本库实证，非推测）

| 证据 | 内容 |
|---|---|
| 未定义符号定位 | `llvm-nm -D -u liblfortran_runtime.so` → 唯一非 libc/libm 未定义符号 `feenableexcept` |
| musl 缺失核对 | `<sysroot>/lib/aarch64-linux-ohos/libc.so` 仅 `fegetexceptflag`，无 `feenableexcept` |
| 补丁 | `patches/0001-musl-feenableexcept-fallback.patch`；`git apply --check -p1` PASS |
| 修复复验 | 应用后编译 rc=0，`feenableexcept` 未定义符号消除（余 157 个全为 libc/libm 标准符号） |
| 消费者验证 | test_package 实机调用 `_lfortran_enable_fpe_traps(1)` 不崩溃；6/6 断言通过 |
| 构建验证 | `conan create` rc=0；`conan-verify` 全门禁 PASS（G0/G1/G2/G3/G4 + L2/L4/L5） |
| 审查证据 | CI #53958 绿；AI review 未发现问题 |

## 推广价值

任何"语言/编译器运行时库落地 OHOS"的场景：
- 引用了 glibc 专属扩展（`feenableexcept`/`fedisableexcept`、`getauxval`、`__libc_*`、
  `execinfo` backtrace 族等）的运行时/基础库在 musl 上出现未定义符号；
- 上游为"编译器 + 运行时"整体工程、在 OHOS 只交付运行时组件时的构建切分。

## 查重与差异化（与 issue 材料一致）

- **查重范围**：`knowledge/graph/` 540 条 + `index.tsv` —— **零 LFortran/libasr 条目**；`knowledge/drafts/` 中 3 条 flang 草稿
  （DRAFT-flang-minimal-runtime-link-contract / DRAFT-ohos-flang-driver-link-overlay /
  DRAFT-flang-hmdfs-parallel-mod-corruption）**全为 flang 路线**，无 lfortran 草稿；
  `musl-glibc-*-comparison*.md` 仅把 `feenableexcept` 列为 GNU 扩展的通用对照，未与编译器运行时库绑定。
- **覆盖判断**：已有知识条目**未完整覆盖**「LFortran 运行时库落地 OHOS」组合；本条目增量 =
  「LFortran 路线的 C 运行时库在 musl 的符号可移植性（feenableexcept → AArch64 FPCR）+ 组件切分」。
- **与 E6339（flang-ohos）差异化**：E6339 = flang/LLVM Flang **工具链的链接契约**
  （tool_requires flang-ohos、`--sysroot`/`-resource-dir`、`cannot open Scrt1.o`/`crtbeginS.o`）；
  本条 = LFortran（**独立技术路线**）**C 运行时库**在 OHOS/musl 上的构建与符号可移植性。二者技术路线、故障机理、
  修复动作**全不同，不重叠**。
- **拟提升编号**：Exxx（最终编号由知识库主编确认）。
