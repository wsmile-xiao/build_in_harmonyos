# tabulate 1.5.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-08
- 状态: built

## 软件概况
- 名称: tabulate（p-ranav/tabulate，C++ header-only 表格渲染库）
- 上游: https://github.com/p-ranav/tabulate
- 版本: 1.5.0（官方 tag v1.5 = commit b35db4cce50a4b296290b0ae827305cdeb23751e，已核验）
- 注意: 本仓库 archives/t/tabulate/0.10.0 为 **Python 同名库**（astanin/python-tabulate），
  与本次 C++ tabulate 1.5.0 无关，仅同名，两者配方不可混用。

## 编译步骤

```bash
# 源码来源：官方 GitHub tag v1.5（v1.5.0 无独立标签，v1.5 即 1.5.0 发布）
# cmake configure（header-only INTERFACE target）
cmake -DCMAKE_SYSTEM_NAME=Linux -DSAMPLES=ON .
# 构建代表示例（编译验证头文件在 OHOS 工具链下可用）
cmake --build . --target employees markdown_export unicode
# 冒烟运行 employees
./employees
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 无 HarmonyOS 平台模块 | 上游 CMakeLists 未注册 OHOS 平台（E092 同类） | `-DCMAKE_SYSTEM_NAME=Linux` 强制走 Linux 分支；tabulate 仅读编译器/平台宏，不影响行为 |

## 源码修改

无补丁（header-only 库，无需平台适配修改）。

## 依赖版本

- 无第三方编译依赖（qualifier: header-only，termcolor/optional_lite/variant_lite 均为内嵌 copy，见 include/tabulate/ 与 LICENSE.*）

## 验证结果

- 上游测试清点（R51）：tabulate 1.5.0 无 tests/ 目录、无 ctest 注册（
  `option(tabulate_BUILD_TESTS OFF)` 声明但未接线任何测试 target）；
  唯一可运行程序为 samples/ 下 **19 个示例**。构建 3 个代表示例
  （employees/markdown_export/unicode）+ 运行 employees 作为上游冒烟验证。
- 消费者测试：test_package/test.cpp 真实调用 Table 构造、add_row、
  列格式化与 MarkdownExporter 导出，9 项断言（表头/单元格/分隔线/导出）。

## 注意事项

- 版本号冲突：制品仓中同名 "tabulate" 若存在 Python 0.10.0 的旧配方，属于另一上游，
  引用方须按上游来源区分。
- R38 判断：构建产物仅头文件（INTERFACE target），无可执行文件 → 不需要 commands.json。
---

**编译结束**: 2026-09-08 01:21
**最终状态**: built
