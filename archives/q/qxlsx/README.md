# QXlsx

QXlsx 是一个基于 Qt 框架的 C++ 库，用于读写 Microsoft Excel (.xlsx) 文件，无需安装 Microsoft Excel 或其他第三方库。

## 功能概述

- **创建 Excel 文件**：从零创建 .xlsx 文件，设置单元格内容、格式、样式
- **读取 Excel 文件**：读取现有 .xlsx 文件的单元格数据
- **单元格操作**：支持文本、数字、日期、公式等数据类型
- **格式设置**：字体、颜色、边框、对齐、合并单元格
- **工作表管理**：创建、删除、复制工作表
- **图表支持**：支持嵌入图表
- **跨平台**：基于 Qt 框架，支持所有 Qt 支持的平台

## OHOS 适配

### 适配要点

1. **构建系统**：QXlsx 使用 CMake 构建系统，源码位于 `QXlsx/` 子目录中
2. **Qt5 依赖**：需要 Qt5 Core 和 Gui 模块，通过 Conan 系统 wrapper 包管理
3. **静态链接**：设置 `BUILD_SHARED_LIBS=OFF` 生成静态库 `libQXlsxQt5.a`，符合 R26 规范
4. **CMake 平台识别**：CMake 不识别 HarmonyOS 平台名称，会输出警告但不影响编译
5. **临时目录**：测试程序输出文件时需使用 `$TMPDIR` 或 `$HOME` 而非 `/tmp`（E002）

### 已知问题

- CMake 检测到系统名称为 HarmonyOS 时会输出 "System is unknown to cmake" 警告，不影响编译
- `/tmp` 目录在 OpenHarmony 上为只读，测试程序保存文件需指定可写路径
- Conan CI profile 中 `tools.cmake.cmaketoolchain:generator=Make` 无效，需在 conanfile.py 中显式指定 `generator="Unix Makefiles"`

## 依赖关系

### 编译依赖
- **Qt5** (5.15.2)：Core 和 Gui 模块
- **CMake** (≥ 3.10)
- **Clang** (15.0.4)：鸿蒙平台工具链

### 运行依赖
- **Qt5** (5.15.2)：Core 和 Gui 运行时库

### Conan 依赖
- `qt/5.15.2@ohpcd/stable`：Qt5 系统 wrapper 包

## 参考资料

- 官方网站：https://github.com/QtExcel/QXlsx
- 源码仓库：https://github.com/QtExcel/QXlsx
- 版本：v1.4.7
- 许可证：MIT
