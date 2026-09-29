# DRAFT-lfortran-nested-cmake-bootstrap（草稿）: 嵌套 cmake 以自建产物为编译器自举运行时——编译器透传环境注入 + 自举产物动态库 DT_RPATH 解析

> 事件族：自举型编译器（嵌套 cmake 以自建二进制为编译器再编译自身运行时）在 OHOS 上的
> 编译器透传与动态库运行期解析。
> 本条为 draft，编号由知识库主编确认，禁止直接 promote。

## 基本信息
- **严重度**: 2
- **类别**: toolchain, cmake, bootstrap, fortran, portability
- **principles**: P-TOOLCHAIN-001
- **similar_to**: E109（OHOS 无 Fortran 编译器）、E242（Fortran .mod 编译器私有 ABI）、DRAFT-odin-llvm-constrained-toolchain-bootstrap（LLVM 后端编译器自举闭环）、DRAFT-13536-libzmq-4.3.5-ohos-ldso-bundle-libs（LD_LIBRARY_PATH 条目致 libc++_shared.so 解析错乱同族）
- **作者**: Hawkninja21
- **来源**: lfortran 0.64.0 适配（2026-09-27，C 类，真机 23 轮全绿 + CI 首跑暴露 LD_LIBRARY_PATH 注入污染）

## 错误特征（预期签名，自举阶段）

```
The C compiler ... is not able to compile a simple test program   ← 嵌套 project() 语言检测找不到编译器
error while loading shared libraries: libLLVM.so                   ← 自建 lfortran 二进制起不来（无系统级搜索）
No CMAKE_Fortran_COMPILER could be found                          ← 自举链断裂
```

## 根因分析

1. **子模式 A — 编译器透传缺口**：lfortran 上游主构建产出 `<build>/src/bin/lfortran` 后，
   以嵌套 cmake（custom target `configure_runtime`/`build_runtime`）把它当作
   `CMAKE_Fortran_COMPILER` 自举编译 Fortran 运行时模块（`src/runtime/*.f90` →
   `lfortran --backend=cpp` 转 C++ → 再经 CXX 编译）。嵌套 configure 只透传有限参数
   （toolchain/prefix/CMAKE_INSTALL_*），**不带 `-DCMAKE_C_COMPILER`/`-DCMAKE_CXX_COMPILER`**；
   嵌套 `project()` 的 `enable_language(C/CXX)` 编译器检测在 OHOS 上找不到默认 cc/c++
   （HNP 工具链不在标准路径）→ configure 失败。
   → 修复：外层 `build()` 以 env 注入 `CMAKE_C_COMPILER`/`CMAKE_CXX_COMPILER`
   （cmake 把同名**环境变量**当初始缓存读取，嵌套 configure 继承外层 self.run 的 env）。

2. **子模式 B — 自举产物动态库解析**：自建 lfortran 二进制动态链 `libLLVM.so`
   （制品仓 clang 包 lib/）。嵌套 cmake 执行它编译 .f90 时，OHOS 无系统级动态库搜索
   （无用户可写的 ld.so 配置；SDK libc 不解析包路径）→ 自举产物起不来。
   → 修复：链接期烘焙 **DT_RPATH** 指向 clang 包 lib/（`-DCMAKE_EXE_LINKER_FLAGS=
   "-Wl,--disable-new-dtags -Wl,-rpath,<clang 包 lib/>"`，与主链接期同源，规避版本混用；
   `--disable-new-dtags` 强制 RPATH 先于 LD_LIBRARY_PATH，防 profile 的 SDK llvm/lib
   里 SDK 版 libLLVM.so 抢先绑定 → LLVM_22 版本失配）。
   **禁 LD_LIBRARY_PATH 注入**（lfortran #13591 CI 首跑实测）：把 clang 包 lib/ 前置进
   LD_LIBRARY_PATH，会让 CI worker 的 HNP cmake 抢绑包内捆绑的 libc++_shared.so
   （比 worker 工具链旧）→ cmake 自身 relocation 符号风暴（`Error relocating
   /data/service/hnp/bin/cmake: ... symbol not found`，顶层/嵌套 cmake 进程均受污染）。
   同机制真机不发作 = 真机 HNP 树较旧、符号恰好够；CI 树更新即爆——**环境注入型动态库
   解析只作用于自建二进制本身才是安全界**。

## 修复模式（可跨库复用）

```python
# conanfile.py build()（摘要）
defs = " ".join([
    # ... 其余 -D ...
    '-DCMAKE_EXE_LINKER_FLAGS="-Wl,--disable-new-dtags -Wl,-rpath,{}"'.format(
        os.path.join(self.dependencies["clang"].package_folder, "lib")),
])
env = {
    "CMAKE_C_COMPILER": cc,        # 真机 HNP clang（或 conf 的 compiler_executables）
    "CMAKE_CXX_COMPILER": cxx,
}
self.run('cmake -B {bdir} -S {src} {defs}'.format(...), env=env)
self.run('cmake --build {bdir} -- -j6', env=env)   # 主二进制链接 libLLVM.so 吃内存,限 -j6
```

> 要点：不改上游源码；环境变量注入是 cmake 的既有语义（初始缓存），非 hack；
> 动态库路径与链接期同源且只作用于自建二进制（RPATH 烘焙），cmake 进程环境零侵入。

## 验证证据

| 证据 | 状态 |
|---|---|
| 配方实现 | env 注入（CMAKE_C/CXX_COMPILER）+ 链接期 DT_RPATH（--disable-new-dtags）已就位；CI 首跑实证 LD_LIBRARY_PATH 前置污染 worker cmake（libc++ 符号风暴）→ 改 RPATH，cmake 环境零侵入 |
| 自举复验 | 真机 conan create 全链通过：configure_runtime/build_runtime 日志在案，lfortran --backend=cpp 转译 + CXX 编译全链 PASS（同接线全量构建 158/158 佐证链） |
| 运行期复验 | test_package 用产出的 lfortran 编译+运行 Fortran 程序 ALL_OK（真机探针全绿） |

## 推广价值

- 任何**自举型编译器/代码生成器**落地 OHOS：嵌套 cmake/custom target 以自建产物为编译器
  再编译自身运行时/绑定（LLVM 系语言实现、IDL/代码生成工具链）；
- 自举产物动态链构建期依赖库（libLLVM/libgcc_s/libstdc++ 等）在无系统级搜索的 OHOS 上的
  运行期解析——优先 RPATH 烘焙，勿 LD_LIBRARY_PATH 注入（后者污染同环境工具链进程，
  libc++ 符号风暴，见子模式 B）。

## 查重与差异化

- **E109** = OHOS 无 Fortran 编译器（事实性缺口）；本条 = 自举产生 Fortran 编译器**之后**的
  嵌套构建透传机制。
- **E242** = Fortran .mod 私有 ABI；本条不涉及 .mod ABI，而是构建拓扑与运行期解析。
- **DRAFT-odin** = 自举闭环的 LLVM **版本门禁 + per-target 符号 + 平台识别**（上游脚本硬编码
  耦合，需 patch）；本条 = 自举闭环的**嵌套 cmake 编译器透传 + 动态库解析**（上游 CMake 缺
  透传，配方层 env 注入即可，无源码 patch）。二者同属「自举闭环落地 OHOS」族但故障点与
  修复动作不同，可组合使用。
- **拟提升编号**：Exxx（最终编号由知识库主编确认）。
