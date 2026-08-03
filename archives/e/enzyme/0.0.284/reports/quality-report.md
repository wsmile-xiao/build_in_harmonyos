# 质量报告 — enzyme 0.0.284

> **报告目的**: 汇总 enzyme 0.0.284 适配的质量状态，支撑 PR !2786 审核。
> **生成日期**: 2026-07-23
> **知识库**: E132 + E216-draft-enzyme-llvm-sdk-lit-ohos

## 适配路径

- **路径 A（基础适配）**: ✅ 成立，基础适配申请
- **路径 B（贡献创新）**: 候选 10 分，适配困难库分析报告（需审核确认）
  - 理由：Enzyme 是 LLVM AutoDiff pass/plugin，上游测试体系依赖完整 LLVM lit/FileCheck/opt/TableGen/tblgen，现有 E120/E132 不能完整覆盖。本适配沉淀了 cmake-overlay/stub-tblgen/AddLLVM stub/test_package nm 符号检查等可复用方法。
- **路径 C（高难度挑战）**: 候选，申请纳入高难库清单，需评审委员会专项终审，最终以官方审核为准
  - 理由：OHOS SDK LLVM 15 缺 .a stub/llvm-tblgen/lit/llvm-lit/完整 C++ API 符号导出，是否算系统级高难以官方审核为准。

## 使用知识库

- **E132**: OHOS SDK lld 运行时依赖 libxml2，LD_LIBRARY_PATH 设置
- **E216-draft-enzyme-llvm-sdk-lit-ohos**: OHOS SDK LLVM 15 缺失完整 LLVM 插件/lit/TableGen 组件（draft，待主编合入）

## 上游测试

- **入口**: enzyme/test/CMakeLists.txt、lit.cfg.py、lit.site.cfg.py.in、ninja check-enzyme、llvm-lit/lit
- **数量**: test/ 下 1523 个测试相关文件，其中主要 .ll/.c/.cpp/.cu/.f90/.mlir 测试文件约 1471（.ll 文件 1180）
- **通过率**: **0/1523**（未执行/未全量执行）
- **未执行原因**: OHOS SDK LLVM 15 缺少完整 lit/FileCheck/llvm-lit/llvm-tblgen 与 LLVM CMake 导出组件
- **替代验证**: test_package nm -D 符号存在性检查 llvmGetPassPluginInfo（1/1，编译期验证通过；runtime 受限于单体 .so 符号导出缺口，见补充说明）

## test_package 统计

- **test_package 测试数**: 1（test_enzyme）
- **实质验证数**: 1（nm -D 符号存在性检查 llvmGetPassPluginInfo，未触发 OHOS SDK LLVM relocation 缺口）
- **断言数**: 3（ENZYME_PLUGIN_LIB 非空 / nm 可执行返回 0 / grep llvmGetPassPluginInfo 命中）
- **R34 合规**: ✅（test.c 接收 ENZYME_PLUGIN_LIB 并执行 nm 检查，失败返回 1；L1e sabotage 确认真依赖）

## 编译状态

- **conan create**: ✅ 通过（exit code 0）
- **构建目标**: LLVMEnzyme-15（shared plugin）/ LLDEnzyme-15（static plugin）/ EnzymeStatic-15（static archive）/ test_enzyme（test 可执行）
- **构建系统**: CMake + cmake-overlay（LLVMConfig.cmake/AddLLVM.cmake/stub-tblgen.sh）

## 补丁

| 补丁 | 类型 | 说明 |
|------|------|------|
| 0001-Enzyme-AdjointGenerator.h.patch | portability | suppress unused variable mod warning |
| 0002-Enzyme-CallDerivatives.cpp.patch | portability | suppress unused variable mod warning |
| 0003-tools-CMakeLists.txt.patch | portability | skip enzyme-tblgen build（LLVM TableGen not available in OHOS SDK） |

## 生成物清理

已 `git rm` 移除：
- .build-closed
- .ci-result.json
- .submit-state.json
- packaging/enzyme-0.0.284-ohos-aarch64.tar.gz
- reports/audit-result.json
- reports/pr-body.md

## 限制条件

1. stub .inc 非真实 AutoDiff 规则（return false 桩），完整功能需 enzyme-tblgen 在完整 LLVM 15 环境生成
2. runtime 加载可能因单体 libLLVM-15.so 符号导出缺口失败（路径 C 候选）
3. 上游 lit 测试 0/1523 无法执行（路径 C 候选）
4. E216 为 draft，尚未由主编审核合入

## 需官方确认

1. OHOS SDK LLVM 15 是否会补充 .a stub / llvm-tblgen / lit/llvm-lit / 完整 C++ API 符号导出？
2. 上述工具链缺口是否算"系统级高难"，路径 C 候选分值以官方审核为准？

---

*evidence: quality-report.md · 2026-07-23 · PR !2786 · E132 + E216 draft*