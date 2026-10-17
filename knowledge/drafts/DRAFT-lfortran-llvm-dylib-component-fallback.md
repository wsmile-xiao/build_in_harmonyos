# DRAFT-lfortran-llvm-dylib-component-fallback（草稿）: 制品仓 LLVM dylib 聚合包无组件目标 + 真机 uname=HarmonyOS 无 cmake Platform 模块的 configure 双失效与回退

> 事件族：LLVM 系编译器在 OHOS 上消费制品仓 LLVM 包时的 cmake configure 检测失效。
> 本条为 draft，编号由知识库主编确认，禁止直接 promote。

## 基本信息
- **严重度**: 2
- **类别**: toolchain, llvm, cmake, portability
- **principles**: P-TOOLCHAIN-001
- **similar_to**: E218（link-only-clang-cpp-monolith）、E286（OHOS SDK LLVM 缺组件→overlay）、DRAFT-odin-llvm-constrained-toolchain-bootstrap（LLVM 后端编译器自举）
- **作者**: Hawkninja21
- **来源**: lfortran 0.64.0 适配（2026-09-27，C 类，真机验证进行中）

## 错误特征（预期签名，configure 期）

```
Could NOT find TARGET LLVMCore                    ← dylib 包无组件导入目标，组件链接路径失效
llvm_map_components_to_libnames(...) → 空列表     ← 链接期无库可用
FATAL_ERROR: LFortran only supports Unix          ← uname=HarmonyOS → UNIX 未置 → 上游判错
```

## 根因分析

1. **子模式 A — LLVM 组件目标缺失**：制品仓 `clang/22.1.8` 包以
   `LLVM_BUILD_LLVM_DYLIB=ON` 构建，交付 `LLVMConfig.cmake`（`LLVM_TARGETS_TO_BUILD=AArch64`）
   与聚合 `libLLVM.so`，但**不导出 LLVMCore 等 per-component 导入目标**。
   lfortran 上游的 LLVM 链接检测走 `llvm_map_components_to_libnames`，组件目标缺失即得空，
   传统组件链接路径失效。上游已内置 **#34593 workaround 分支**（检测 `TARGET LLVMCore`
   缺失 → 回退直链 `libLLVM.so` 聚合库），因此适配动作是**让检测命中回退分支**而非改上游：
   - `LLVM_DIR` 指向**包内** `lib/cmake/llvm`（不得指向真机 SDK 的 LLVM 15——
     版本/布局与包不同，混用即 ABI 错乱，odin bad_cast 误诊同款教训）；
   - `WITH_LLVM=yes` + `WITH_TARGET_AARCH64=yes`，x86/wasm 全关——与包
     `LLVM_TARGETS_TO_BUILD=AArch64` **严格对齐**（请求包未构建的后端同样会失败）。

2. **子模式 B — cmake Platform 模块缺失**：真机 `uname -s=HarmonyOS`，cmake
   `Modules/Platform` 无 HarmonyOS 条目。原生编译（不设 `CMAKE_SYSTEM_NAME`、
   `CMAKE_CROSSCOMPILING=FALSE`）时 UNIX 等变量未置，上游 `if(NOT UNIX)` 判错 FATAL。
   修复=CMAKE_MODULE_PATH 注入配方生成的 `Platform/HarmonyOS.cmake` 桩
   （单行 `include(Platform/Linux)`，置 UNIX=1 与 Linux 链接/rpath 规则），
   与 `clang/22.1.8` 真机构建同款路线。

## 修复模式（可跨库复用）

```python
# conanfile.py build()（摘要）
_pm = os.path.join(self.build_folder, "_cmake_modules")
os.makedirs(os.path.join(_pm, "Platform"), exist_ok=True)
open(os.path.join(_pm, "Platform", "HarmonyOS.cmake"), "w").write(
    "include(Platform/Linux)\n")
llvm_dir = os.path.join(self.dependencies["clang"].package_folder,
                        "lib", "cmake", "llvm")
defs = ' '.join([
    '-DCMAKE_MODULE_PATH="{}"'.format(_pm),
    '-DLLVM_DIR="{}"'.format(llvm_dir),
    "-DWITH_LLVM=yes", "-DWITH_TARGET_AARCH64=yes",
    "-DWITH_TARGET_X86=no", "-DWITH_TARGET_WASM=no", ...])
```

> 要点：不改上游源码（回退分支上游已有）；平台桩为配方生成文件，不进上游；
> 不设 `CMAKE_SYSTEM_NAME`（避免交叉编译误判与 R26 静态系统库规则误触发）。

## 验证证据

| 证据 | 状态 |
|---|---|
| 包 LLVMConfig 核对 | `clang/22.1.8` 包 `LLVMConfig.cmake`：AArch64-only、dylib 聚合、无 LLVMCore 组件目标（已核对） |
| configure 复验 | 真机 conan create 进行中，configure 日志待回填 |
| 产物复验 | `bin/lfortran` 的 libLLVM.so 依赖与符号解析待回填 |

## 推广价值

- 任何**消费制品仓 LLVM 包的编译器/代码生成器**（cling、mlton、swift 类、其他
  LLVM 后端语言实现）在 dylib-only 包上的组件解析失效；
- 任何 cmake 工程在 OHOS 真机原生编译时 uname 非 Linux 导致的 Platform/UNIX 判定失真。

## 查重与差异化

- **E218** = CastXML 双 monolith（libLLVM-15 + libclang-cpp）CommandLine 重复注册崩溃；
  本条 = 单一 dylib 包下**组件目标缺失**的 configure 回退。机制、故障点、修复动作全不同。
- **E286** = **真机 SDK** LLVM 15 缺组件（LLVMExports .a stub/TableGen/lit）→ cmake-overlay
  整体替换 LLVMConfig + IMPORTED 单体目标 + tblgen 桩；本条 = **制品仓 conan 包** LLVM 22
  的 LLVMConfig 完整（仅 dylib 无组件目标），走上游 #34593 回退分支，**无需 overlay、
  无 TableGen/lit 需求**（lfortran 不用 TableGen）。
- **DRAFT-odin** = 自举闭环的 LLVM 版本门禁 + per-target 符号 patch + conanrun 注入；
  本条 = configure 期组件解析与平台判定。可组合使用（odin 走制品仓 LLVM 包时同样可命中
  子模式 A）。
- **拟提升编号**：Exxx（最终编号由知识库主编确认）。
