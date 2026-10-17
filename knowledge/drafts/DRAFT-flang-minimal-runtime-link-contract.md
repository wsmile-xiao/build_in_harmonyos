# DRAFT-flang-minimal-runtime-link-contract（草稿）: flang-ohos 精简运行集链接契约

> 事件族：含 Fortran 的库在 OHOS 设备原生构建（tool_requires flang-ohos）时的
> 编译/链接注入契约。本条为 draft，编号由知识库主编确认。
> **附带 E109 勘误注记（交知识库主编）见文末。**

## 基本信息
- **严重度**: 2
- **类别**: toolchain, fortran, ohos, linking
- **principles**: P-TOOLCHAIN-001（必须使用 LLVM 工具链）
- **similar_to**: E242（Fortran .mod ABI/tool_requires 模式）、E258（LLVM 工具链真机原生构建组合）
- **作者**: GoliWie
- **来源**: devicexlib 0.9.1 适配（run devicexlib-0.9.1，2026-09-11）

## 错误特征（裸调用 flang，设备实测 P2-A，EXIT=1）
```
ld.lld: error: cannot open Scrt1.o: No such file or directory
ld.lld: error: cannot open crti.o: No such file or directory
ld.lld: error: cannot open crtbeginS.o: No such file or directory
ld.lld: error: unable to find library -lm
ld.lld: error: cannot open <flang>/lib/clang/20/lib/aarch64-linux-ohos/libclang_rt.builtins.a: No such file or directory
ld.lld: error: unable to find library -l:libunwind.a
ld.lld: error: unable to find library -lc
ld.lld: error: cannot open crtendS.o / crtn.o
flang-20: error: linker command failed with exit code 1
```
另：无任何 Fortran 编译器注入时，CMake 在 project() 处报
`No CMAKE_Fortran_COMPILER could be found`（reports/builder/phase-a-configure.log）。

## 根因分析

flang-ohos/20.1.0 是设备原生 LLVM Flang **精简运行集**：仅 bin/flang +
libLLVM/libMLIR/libclang-cpp.so.20.1 + libFortranRuntime/Decimal.a——**不含**
clang builtins、crt 对象、libomp。因此：

1. 前端自足（编译 .f90 → .o 可过），**链接必败**：crt 对象（sysroot）、
   libclang_rt.builtins.a（resource-dir）、libunwind.a（SDK llvm/lib）全部缺位。
2. 正确契约 = 三段注入：
   - 编译：`--sysroot=<SDK>/native/sysroot -resource-dir=<SDK>/native/llvm/lib/clang/15.0.4`
   - 链接：`-L<SDK>/native/llvm/lib/aarch64-linux-ohos -L<SDK>/native/llvm/lib
     -L<flang>/lib -lFortranRuntime -lFortranDecimal`
   - 运行：`LD_LIBRARY_PATH=<SDK>/native/llvm/lib:<flang>/lib`
     （前者补 lld 的 libxml2.so.16，后者补 flang 的 libLLVM/libMLIR/libclang-cpp）
3. 设备实测同一程序：裸调用 EXIT=1（上述错误组）→ 注入后 EXIT=0 并打印
   "flang link contract ok"（P2-B，reports/builder/draft-probes.log）。
4. 纯 Fortran 静态库（无对外 C 接口，如 devxlib）的 CMake
   `find_package(LAPACK/OpenMP REQUIRED)` 依赖 Find 模块链接探测——同一组坑；
   需确定性 shim 或 STATIC_LIBRARY try_compile 规避。

## 推荐契约（优先级 1）：tool_requires + generate() 显式注入

```python
def build_requirements(self):
    self.tool_requires("flang-ohos/20.1.0")
def generate(self):
    flang = .../dependencies.build["flang-ohos"].package_folder
    tc.variables["CMAKE_Fortran_COMPILER"] = <flang>/bin/flang
    tc.variables["CMAKE_Fortran_FLAGS"] = ("--target=aarch64-linux-ohos "
        "--sysroot=<SDK>/native/sysroot -resource-dir=<SDK>/native/llvm/lib/clang/15.0.4")
    tc.variables["CMAKE_EXE_LINKER_FLAGS"] = ("-L<SDK>/native/llvm/lib/aarch64-linux-ohos "
        "-L<SDK>/native/llvm/lib -L<flang>/lib -lFortranRuntime -lFortranDecimal")
def build(self):
    os.environ["LD_LIBRARY_PATH"] = <SDK>/native/llvm/lib + ":" + <flang>/lib
def package(self):
    # libFortranRuntime.a / libFortranDecimal.a 复制进包内 lib（消费方闭包）
```
仓内先例：openblas 0.3.34、lapack 3.12.1；devicexlib 0.9.1 按此 CI L0-L5 全 pass。

## 备选（优先级 2）：确定性 Find 模块 shim

上游硬编码 `find_package(LAPACK/OpenMP REQUIRED)` 且默认探测不可靠时，在
generators 目录提供 FindLAPACK.cmake / FindOpenMP.cmake shim（CMAKE_MODULE_PATH
指向）：LAPACK 映射 conan lapack 包 IMPORTED 目标（闭包带 libblas.a 与
Fortran 运行时）；OpenMP 提供空 INTERFACE IMPORTED 目标。**诚实边界**：仅当
CPU-only 路径不使用 OpenMP 编译开关时成立（devicexlib 即此形态，recipe 注释
已写明"shim 即最终语义"）；若库真正消费 OpenMP，必须走推荐契约补 libomp 探测。

## 禁止

- **forbid_1**: 把 FindLAPACK/FindOpenMP 默认链接探测当作链接闭包成立的证据 ——
  精简运行集下探测非确定性失败、报错远离真实缺口，或掩盖缺失闭包后移爆发。
- **forbid_2**: 把 flang 二进制/so 散装复制出 conan 包、或在 profile/shell rc
  全局持久注入 flang 的 LD_LIBRARY_PATH —— 脱离包管理 + 污染同机 clang/lld
  加载环境（SDK lld 对 libxml2.so.16 路径敏感）。

## 判别/验证序列（设备自包含，P2-A/P2-B 已实测）

```bash
SDK=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native
FLANG=/storage/Users/currentUser/.conan2/p/flang74dc24ecd515c/p   # conan 缓存包
printf 'program hello\n  print *, "flang link contract ok"\nend program\n' > hello.f90
# ① 裸调用：预期 Scrt1.o/builtins/libunwind 一组错误，EXIT=1
env LD_LIBRARY_PATH=$SDK/llvm/lib:$FLANG/lib $FLANG/bin/flang hello.f90 -o hello_a
# ② 契约注入：预期 EXIT=0 且运行打印
env LD_LIBRARY_PATH=$SDK/llvm/lib:$FLANG/lib $FLANG/bin/flang --sysroot=$SDK/sysroot \
  -resource-dir=$SDK/llvm/lib/clang/15.0.4 hello.f90 -o hello_b \
  -L$SDK/llvm/lib/aarch64-linux-ohos -L$SDK/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos \
  -L$FLANG/lib && ./hello_b
```

## E109 勘误注记（maintenance note，交知识库主编；本 run 不直接改 knowledge/doc/E109.md）

E109（OHOS 无 Fortran 编译器）的 rec_approach——"无法通过本地命令解决……标记
为 failed，等待官方支持"——**已被仓内事实推翻**：flang-ohos/20.1.0（设备原生
LLVM Flang tool 包，archives/f/ 收录，2026-07-24 built）配合本条链接契约，已支撑
openblas（×3 版本）、lapack、mpich、mumps、scalapack、arpack-ng、libxc、cblas、
r-base、packmol、fortran-shlex、acepack、alfa 共 **14 处消费 recipe** 与本 run 的
devicexlib 0.9.1 成功适配（CI Pass rate 100%、8 套件 176/176 上游测试）。建议 E109 增补勘误段：
"含 Fortran 的库在 OHOS 的默认路径为 tool_requires flang-ohos/20.1.0 + 本契约注入
（见 DRAFT-flang-minimal-runtime-link-contract），failed-and-wait 路线仅作最终兜底"。
另：E109 关联的 knowledge/doc/E535.md 在当前仓库不存在（knowledge/graph 止于
E317），主编复核引用完整性时一并处理。

## 关键词
flang-ohos, flang-new, tool_requires, sysroot, resource-dir, FortranRuntime,
FortranDecimal, libclang_rt.builtins, Scrt1.o, libunwind, LD_LIBRARY_PATH,
libLLVM, libMLIR, libclang-cpp, FindLAPACK, FindOpenMP, 精简运行集, E109 勘误
