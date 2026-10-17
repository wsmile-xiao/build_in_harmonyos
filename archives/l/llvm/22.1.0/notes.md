# llvm 22.1.0 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出 `libLLVM.so`（聚合动态库）+ 组件库 + 工具 + cmake 导出，AArch64 后端，RTTI 开。
- **直接动因**：llvmlite 0.48.0 的 `ffi/CMakeLists.txt` 硬卡 `LLVM_VERSION_MAJOR == 22`
  （`LLVMLITE_SUPPORTED_LLVM_VERSION_DEFAULT 22`），制品仓当时只有 `llvm/20.1.0`。

## 为什么恰好是 22.1.0（不是 22.1.8）
不是挑「最新的 22.x」，是**对齐上游实际发布的那一版**：拆 PyPI 上
`llvmlite-0.48.0-cp312-cp312-manylinux_2_27_aarch64.whl` 里的 `libllvmlite.so`，
字符串是 `LLVM version 22.1.0`。对齐它可以把「行为差异是不是 LLVM 补丁版本漂移导致的」
这一整类问题从后续排查中摘掉。

## 关键适配（沿用 20.1.0，逐条在 22.1.0 上复核）
- `cmake/config.guess` 用 stub 覆盖：设备 `uname -s = HarmonyOS`，原脚本非零退出而
  `config-ix.cmake` 无条件调用它 → FATAL。22.1.0 源码树里该文件仍在原位。
- 提供 `Platform/HarmonyOS.cmake`（`include(Platform/Linux)`）：cmake 无此平台模块 →
  `UNIX` 未置 → LLVM 报 "Unable to determine platform"。
- **不设 `CMAKE_SYSTEM_NAME`**：保持 native，`CMAKE_CROSSCOMPILING=FALSE`，
  `llvm-tblgen` 原生编+跑——这正是选真机原生而非交叉的核心收益。
- `LLVM_BUILD_LLVM_DYLIB` + `LLVM_LINK_LLVM_DYLIB`：工具从各自静态内嵌降到链
  `libLLVM.so`，制品体积大降（否则 `conan_package.tgz` 会撞制品仓单文件上限，20.1.0 曾被 413 拒）。
- `LLVM_ENABLE_RTTI=ON`：llvmlite 必需（LLVM 默认 OFF）。
- `LLVM_PARALLEL_LINK_JOBS=4`：`libLLVM.so` 链接极吃内存，设备 31G/20 核，防 OOM。

## 形态：shared / static

`shared` 在 20.1.0 是个**哑巴选项** —— 声明了、`configure()` 里也按它删 fPIC，但 `build()`
从头到尾没读过它，`-o llvm/*:shared=False` 拿到的仍旧是 shared 构建。声明了却不生效
比没声明更糟：消费方以为自己选了静态形态。本版把它接上：

| | `shared=True`（默认） | `shared=False` |
|---|---|---|
| `LLVM_BUILD/LINK_LLVM_DYLIB` | ON —— 出 `libLLVM.so`，LLVM 自己的工具链它 | OFF |
| `LLVM_BUILD_TOOLS` / `INSTALL_UTILS` | ON | **OFF** |
| 定位 | 通用形态（带 llvm-config/llc/FileCheck 等工具） | **给人链的形态** |
| `cpp_info.libs` | `["LLVM"]` | `[]`（组件经 LLVMConfig.cmake 消费） |

静态形态关掉 tools 的原因：不出聚合动态库时，90 个工具会各自静态内嵌 LLVM，
`bin/` 从几十 MB 撑到 ~892MB。要工具请用 shared 形态。

### 已实证：shared 形态就够 llvmlite 静态链，不必出静态包

真机出包后逐条查（`conan create` rc=0，package id `01d92cf349a0…`）：

| 核查项 | 结果 |
|---|---|
| 组件静态库 `.a` | **110 个 / 171M**（`libLLVMAArch64CodeGen.a` 10.4M、`libLLVMCore.a` 8.9M、`libLLVMMC.a` 2.4M） |
| `libLLVM.so` | 81M（另有 `libLLVM-22.so`、`libLLVM.so` 两条软链） |
| 包总大小 | **372M** = include 50M + bin 74M + lib 250M |
| `LLVMConfig.cmake` | `set(LLVM_LINK_LLVM_DYLIB ON)` |

**判据是最后一条，不是前三条**——按 llvmlite 的原样跑一次：

```cmake
find_package(LLVM REQUIRED CONFIG)
llvm_map_components_to_libnames(libs core mcjit native irreader target)
```
```
-- LLVM_PACKAGE_VERSION=22.1.0
-- LLVM_VERSION_MAJOR=22
-- MAPPED=LLVMCore;LLVMMCJIT;LLVMIRReader;LLVMTarget;LLVMAArch64CodeGen;...
```

吐的是**组件静态库名，不是 `LLVM` dylib**。`LLVM_LINK_LLVM_DYLIB=ON` 只改 LLVM
自己那 90 个工具链谁，不改 `llvm_map_components_to_libnames` 的映射。
llvmlite 默认 `LLVMLITE_SHARED=OFF`、走的正是这个宏，所以它会链到那 110 个 `.a`
上，得到与上游 manylinux wheel 同形态的自包含产物。

→ **静态形态（`-o shared=False`）留作可选项，但没有理由跑**：它只会得到一个更大、
更难过 cnb 单文件上限的包，而换来的东西这个包已经给了。

## 状态
真机 `conan create` 通过（含 test_package：dlopen `libLLVM.so` + 解析
`LLVMContextCreate` 符号）。**未上传**——制品仓 append-only，等人确认。
