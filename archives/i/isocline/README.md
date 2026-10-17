# isocline - HarmonyOS 编译记录

## 概述

isocline 是 Daan Leijen 编写的纯 C readline 替代库（MIT 许可），提供多行编辑、历史记录、文件名/自定义补全、Unicode、撤销/重做、增量历史搜索、行内提示、语法高亮、括号匹配、bbcode 富文本终端输出等功能，可作为 GNU readline 的轻量替代品。

**编译状态**：适配中（配方已完成，待真机预检验证）

## 编译环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS PC (OHOS) aarch64 |
| 编译器 | clang 15 |
| 三元组 | aarch64-linux-ohos |
| 构建系统 | CMake（上游自带 CMakeLists.txt，无需覆盖） |

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.1.0 | built | 首次适配（上游 tag v1.1.0，2026-04-21） |

## 说明

- 上游 CMakeLists 恒同时构建 `isocline` 静态库与 `isocline_shared` 共享库（`OUTPUT_NAME` 均为 `isocline`），配方按 `shared` 选项裁剪对侧产物，保证单包单形态
- 上游 `IC_BUILD_TESTS` 构建的 `example` / `test_colors` 为交互式演示程序（需真实 TTY），未接入任何自动化测试框架，配方以 `IC_BUILD_TESTS=OFF` 关闭其构建，覆盖由 test_package 消费者断言测试提供
- 上游确无测试套件（审计见 `1.1.0/test_package/MANIFEST.yml` 的 `upstream_test_audit`），`build()` 不调用 `cmake.test()`
