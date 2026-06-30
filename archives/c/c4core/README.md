# c4core

跨平台底层 C++ 工具库 — 提供格式化、类型操作、编解码（base64, UTF）等底层辅助功能的静态库。

- **主页**: https://github.com/biojppm/c4core
- **语言**: C++11
- **构建系统**: cmake
- **类型**: 静态库 (libc4core.a)
- **无外部依赖**

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|---------|--------|
| 0.2.10 | published | 2026-06-13 | 1 |

## 鸿蒙适配说明

- c4core 是 rapidyaml (ryml) 的上游依赖
- 需要修改 cmake/c4Project.cmake 添加 HarmonyOS 平台支持（补丁：0001-cmake-c4Project.cmake.patch）
- 发布源码包不含测试框架（需 ryml 等额外依赖）
- 必须使用 out-of-source 构建（cmake 项目标准做法）

## 功能验证

- 自定义功能测试程序验证：版本宏、substr 操作、format 操作均通过 ✅
- cmake 包查找验证通过 ✅