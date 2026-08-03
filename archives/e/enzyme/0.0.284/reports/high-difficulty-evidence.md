# 高难证据报告 — enzyme 0.0.284

> **报告目的**: 证明 enzyme 适配不是普通路径 A，支撑路径 B（贡献创新，10 分候选）与路径 C（高难度挑战候选，需评审委员会专项终审）。
> **生成日期**: 2026-07-23
> **知识库**: E216-draft-enzyme-llvm-sdk-lit-ohos

## 为什么不是普通路径 A

普通路径 A（基础适配）的典型特征：configure/make 通过、少量平台宏补丁、上游测试可执行或少量 skip。enzyme 适配远超此范围：

| 维度 | 普通 A | enzyme 实况 |
|------|--------|------------|
| 构建系统 | autotools 或简单 CMake | LLVM CMake 函数体系（add_llvm_library/tablegen/configure_lit_site_cfg 等） |
| 依赖 | 系统/Conan 依赖 | OHOS SDK LLVM 15 缺 .a stub/llvm-tblgen/lit/FileCheck |
| 代码生成 | 无 | TableGen .inc 文件（BlasDerivatives/CallDerivatives/BlasAttributor 等 8 个） |
| 上游测试 | make check 或 ctest | 1523 个 lit 用例，需 lit/FileCheck/llvm-lit |
| runtime | 直接链接 | LLVM pass plugin，dlopen 因单体 .so 符号导出缺口不可行，改用 nm 静态检查 |
| 补丁规模 | 数行平台宏 | cmake-overlay 3 文件（LLVMConfig/AddLLVM/stub-tblgen）+ 3 patches |

## 路径 B 已解决/沉淀的可复用方法

1. **cmake-overlay 模式**：当 SDK 的 CMake config 不完整（引用不存在的 .a stub）时，用 overlay 目录覆盖 LLVMConfig.cmake，创建指向单体 .so 的 IMPORTED target。此模式可复用于其他 LLVM pass/plugin 类库（Polly、MLIR plugins 等）。
2. **stub-tblgen.sh 生成 .inc 桩**：当 SDK 缺 llvm-tblgen 时，用 shell 脚本生成最小 .inc 文件（return false 的函数桩），使源码编译通过。需 chmod +x，否则 execute_process 触发 permission denied 生成空文件。
3. **AddLLVM.cmake stub 函数**：实现 tablegen()/add_llvm_library()/add_public_tablegen_target()/configure_lit_site_cfg()/get_llvm_lit_path() 等 LLVM CMake 函数，使 Enzyme 的 CMakeLists.txt 可解析。
4. **test_package nm 符号检查模式**：LLVM pass plugin 的消费者视角验证模式——conanfile.py 定位包产物路径，以 ENZYME_PLUGIN_LIB 环境变量传入 test_enzyme，test.c 执行 nm -D 检查 llvmGetPassPluginInfo 符号存在性（不触发 OHOS SDK LLVM relocation 缺口）。满足 R34，可复用于其他 LLVM plugin。
5. **上游 lit 测试资产清单化**：当 lit 无法执行时，仍精确统计 test/ 下文件数（1523）与主要测试源文件数（1471），在 PR 正文写 0/1523（未执行），不勾选"上游无测试"。

## 路径 C 候选依据

### C-1: LLVM pass/plugin 完整工具链缺口

enzyme 是 LLVM AutoDiff pass/plugin，其完整构建与测试依赖：
- LLVMExports .a stub（LLVMDemangle.a/LLVMSupport.a/LLVMCore.a 等）→ OHOS SDK 缺失
- llvm-tblgen 二进制（TableGen 代码生成）→ OHOS SDK 缺失
- lit/FileCheck/llvm-lit（上游 1523 测试用例执行）→ OHOS SDK 缺失
- 单体 libLLVM-15.so 导出完整 LLVM C++ API 符号（plugin runtime 加载）→ OHOS SDK 部分缺失

### C-2: 完整 lit testsuite

上游 enzyme/test 下 1523 个测试文件（其中 1180 个 .ll 用例），覆盖 ReverseMode/ForwardMode/BatchMode/ActivityAnalysis/BCLoader 等多套件。OHOS SDK 无 lit/llvm-lit，0/1523 可执行。

### C-3: TableGen/tblgen

Enzyme 使用 LLVM TableGen 描述 BLAS/Call/Binop/Intrinsic/Instruction 的 derivative rules，需 llvm-tblgen 生成 .inc 文件。本适配用 stub-tblgen.sh 生成 return false 桩，**非真实 AutoDiff 规则**——完整功能需外部完整 LLVM 15 环境。

### C-4: FileCheck/opt

lit 测试依赖 FileCheck（输出比对）和 opt（IR 处理）。FileCheck 在 /data/service/hnp/bin/ 存在但非 SDK 自带；opt 未验证。

### C-5: LLVMExports/LLVMDemangle

LLVMExports.cmake 引用 LLVMDemangle.a 等 .a stub，OHOS SDK 仅提供单体 libLLVM-15.so，无任何 .a 文件。本适配用 cmake-overlay 跳过 LLVMExports.cmake。

### C-6: OHOS SDK 工具链缺口

上述 C-1 至 C-5 嚀属 OHOS SDK LLVM 15 的组件缺口，**是否算系统级高难，需官方确认**。

## 已完成验证

| 项 | 状态 | 证据 |
|----|------|------|
| conan create 编译 | ✅ | Built target LLVMEnzyme-15/LLDEnzyme-15/EnzymeStatic-15/test_enzyme |
| cmake-overlay 跳过 LLVMExports | ✅ | LLVMConfig.cmake 创建 IMPORTED target 指向 libLLVM-15.so |
| stub-tblgen.sh 生成 .inc | ✅ | BlasDerivatives.inc/BlasAttributor.inc 含 return false 桩 |
| test_package 编译期验证 | ✅ | test_enzyme 可执行文件构建成功 |
| 上游测试资产统计 | ✅ | 1523 文件 / 1471 主要测试源 / 1180 .ll 用例 |
| E216 draft 知识库 | ✅ | graph/draft/E216-draft-enzyme-llvm-sdk-lit-ohos.kv + doc/E216.md |

## 未完成项和恢复条件

| 项 | 状态 | 恢复条件 |
|----|------|---------|
| test_package runtime 验证 | ⚠️ | 单体 libLLVM-15.so 未导出部分 LLVM C++ API 符号，dlopen(libLLVMEnzyme-15.so) relocation 失败。改用 nm 静态符号检查（ENZYME_PLUGIN_LIB 传入路径，不触发 relocation） |
| 上游 lit 测试执行 | ❌ | OHOS SDK 缺 lit/llvm-lit/llvm-tblgen，0/1523。需 SDK 补充工具（路径 C 候选） |
| stub .inc 替换为真实 TableGen 输出 | ❌ | 需外部完整 LLVM 15 环境用 enzyme-tblgen 预生成 8 个 .inc，作为 patches 打入 |

## 需官方确认的问题

1. OHOS SDK LLVM 15 是否会补充 .a stub 文件以支持 LLVMExports.cmake 标准 find_package？
2. OHOS SDK LLVM 15 是否会提供 llvm-tblgen 以支持 TableGen 代码生成？
3. OHOS SDK LLVM 15 是否会提供 lit/FileCheck/llvm-lit 以支持上游 LLVM lit 测试体系？
4. 单体 libLLVM-15.so 是否会导出完整 LLVM C++ API 符号以支持插件 runtime 加载？
5. 上述工具链缺口是否算"系统级高难"，路径 C 候选分值以官方审核为准？

---

*evidence: high-difficulty-evidence.md · 2026-07-23 · PR !2786 · E216 draft · 路径 B 10 分候选 · 路径 C 高难挑战候选/需专项终审*