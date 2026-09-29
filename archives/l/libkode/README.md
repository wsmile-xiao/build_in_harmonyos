# libkode

libkode 是一个 C++/Qt 库，用于**程序化的 C++ 代码生成**和 **XML/XSD 模式解析**。它最初来自
[kode](https://github.com/cornelius/kode) 项目和 [KDSOAP](https://github.com/KDAB/KDSoap)
项目，后被拆分为独立仓库以方便两个项目共同演进。

## 功能概述

- **代码生成**（`code_generation/`，库 `kode`）：以 `KODE::` 命名空间的抽象类（`Class`、
  `File`、`Code`、`Function`、`MemberVariable`、`Enum`、`Printer` 等）描述并打印 C++11 及
  以上规范的类/源码。
- **XML 通用**（`common/`，库 `xmlcommon`）：`QName`、`ParserContext`、`NSManager`、
  `FileProvider` 等 XML/SOAP 解析辅助。
- **XSD 模式解析**（`schema/`，库 `xmlschema`）：`XSD::` 命名空间的 `Element`、`Attribute`、
  `ComplexType`、`SimpleType`、`Parser` 等，将 XML Schema（XSD）映射为 C++ 结构。

## 项目使用者

- [kode](https://github.com/cornelius/kode)
- [KDSOAP](https://github.com/KDAB/KDSoap)
- [nut-codegen](https://github.com/martonmiklos/nut_codegen)

## OHOS 适配

- 构建系统为 **CMake**（C++17），依赖 Qt5 或 Qt6 的 `Core`/`Network`/`Xml`/`Test` 模块。
  本仓库在 HarmonyOS PC 上以 **Qt6**（`-Dlibkode_QT6=ON`，依赖 `qtbase/6.11.1`）构建。
- qtbase 使用 `cmake_find_mode=none`，配方手工写 `conan_cmakedeps_paths.cmake` 预置
  `CMAKE_PREFIX_PATH` 使 `find_package(Qt6 COMPONENTS Core Network Xml Test)` 生效。
- 上游无 `install()` 规则：`0001-add-install-rules.patch` 补齐三个静态库与头文件的安装。
- 产物为三个静态库 `libkode.a` / `libxmlcommon.a` / `libxmlschema.a` 及扁平
  `include/` 头文件（上游顶层设置 `libkode_LIBRARY_QTID` 但子目录引用 `${kode_LIBRARY_QTID}`，
  变量名不匹配导致 QTID 恒为空，故库名不带 `-qt6` 后缀）。
- 上游自带 3 个 QtTest 自动化测试（ctest 条目），纯逻辑（拷贝/移动/赋值），无窗口、网络依赖，
  在 `conan create` 的 `build()` 内以 offscreen QPA 运行。

## 依赖关系

- 编译依赖：Qt6（`Core`/`Network`/`Xml`/`Test`）→ `qtbase/6.11.1`。
- 无其它外部库依赖。

## 参考资料

- 官网：<https://github.com/cornelius/libkode>
- 上游源码：<https://github.com/cornelius/libkode>（git snapshot 版本，无 tag 发布）
