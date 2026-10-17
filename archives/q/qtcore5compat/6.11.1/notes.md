# qtcore5compat 6.11.1 适配笔记

## 基本信息

- 软件名称: qtcore5compat（Qt Core5Compat，Qt5 兼容 API 模块）
- 版本: 6.11.1
- 构建系统: cmake
- 编译日期: 2026-08-12
- 状态: published
- 上游仓库: https://download.qt.io/official_releases/qt/6.11/6.11.1/submodules/qt5compat-everywhere-src-6.11.1.tar.xz
- 适配路径: 路径 A（基础适配）

## 编译步骤

1. `ohc-run.py init-build qtcore5compat 6.11.1 --url=https://mirrors.tuna.tsinghua.edu.cn/qt/official_releases/qt/6.11/6.11.1/submodules/qt5compat-everywhere-src-6.11.1.tar.xz`
2. CMake 配置（conan create 内部）：`QT_QMAKE_TARGET_MKSPEC=harmonyos-clang`、`Qt6_DIR=<qtbase 包>/lib/cmake/Qt6`、`CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=BOTH`
3. `cmake --build` 生成 libQt6Core5Compat.so
4. ctest 运行上游 13 个 auto tests（13/13 通过）
5. `conan-verify` 8 道门禁（G0-G4 + L2/L4/L5）全部通过

## 依赖

- qtbase/6.11.1（提供 Qt6Config.cmake 与 harmonyos-clang mkspec，Core 组件 REQUIRED）

## 关键适配点

1. **源码包命名差异**：Qt 6.11.1 镜像中子模块包名为 `qt5compat-everywhere-src-6.11.1.tar.xz`（仓库名 qt5compat、CMake 项目名 Qt5Compat），而 conan 包名使用模块名 qtcore5compat。
2. **复用 qtbase 的 Qt6 构建基础设施**：qtbase 包已安装完整 Qt6Config.cmake 与 harmonyos-clang mkspec，qtcore5compat 通过 `Qt6_DIR` 指向 qtbase 包即可交叉编译，无需重复打 mkspec 补丁。
3. **仅 REQUIRED Core 组件**：qt5compat 的 find_package 中 Network/Xml/Gui/Widgets/Quick 均为 OPTIONAL，只有 Core 是 REQUIRED，纯 Core 依赖即可构建。
4. **测试 NEEDED 相对路径修复**：Qt 6.11 测试二进制记录相对 NEEDED（`../../../../../../lib/libQt6Core5Compat.so`），从测试目录解析到 `<build-root>/lib`；单配置 cmake_layout 下库在 `<build-root>/<config>/lib`，配方在 ctest 前创建 `<build-root>/lib` 符号链接并导出 LD_LIBRARY_PATH。

## 验证结果

- conan create 干净构建通过
- 上游 auto tests: 13/13 通过（100%）
- test_package 消费者测试（QRegExp/QLinkedList/QStringRef/QTextCodec 15 条断言）: ALL PASSED
- conan-verify: G0-G4 全 PASS
- pre_pr_audit W4 审计: P0=0, P1=0, P2=2（已修复）

## 最终状态

built → published（conan-verify 通过）

## 编译结束

qtcore5compat 6.11.1 适配完成：conan-verify G0-G4 全 PASS，上游 13/13 测试通过，test_package 消费者测试 ALL PASSED。
