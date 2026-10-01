# qconf

QConf — 为 qmake 工程生成「友好的 configure 脚本」的 Qt5 命令行工具。

## 概述

qconf 读取一份 `.qc` XML 描述（工程名、`.pro` 文件、可选项、依赖、模块目录等），
生成一个自包含的 `configure` 脚本（外加 `configure.exe` 包装）。生成物把
`conf4.cpp` / `conf4.h` / `conf4.pro`（Qt5 路径）内嵌其中，在**下游工程**里
执行 `./configure && make` 即可完成选项解析与 qmake 构建。

qconf 自身是控制台程序：`QT -= gui`、`QT += xml`、`CONFIG += console`，
不依赖 GUI/X11。

## 已编译版本

- **2.5** (2026-10-01) — clang 15.0.4 / libc++，qmake（`-spec linux-clang`），OHOS aarch64

## 关键信息

- **源码**: https://github.com/psi-im/qconf （tag `v2.5` = `a06a3ca`）
- **构建系统**: qmake（`qconf.pro`，in-source build）
- **依赖**: `qt5-qtbase/5.15.2.2`（Qt5Core + Qt5Xml + qmake/moc/rcc）；
  传递 zlib/1.3.1、dbus/1.14.10 → expat/2.8.2
- **平台**: aarch64 (HarmonyOS / OpenHarmony)

## 鸿蒙适配要点

1. `_setup_qmake_modules()`：qt5-qtbase 包内 `mkspecs/modules/*.pri` 记录的是构建期
   绝对路径，直接使用会 `Unknown module(s) in QT: core xml` → 改写为包内路径并经
   `QMAKEMODULES` 暴露。
2. 运行期数据布局：qconf 以 `applicationDirPath()` 下的 `conf/` + `modules/` 做就地检测，
   Conan 包无固定安装前缀 → `conf/`、`modules/` 与二进制同装 `bin/`，包自包含且与 cwd 无关。
3. 产物 RPATH 指向构建期路径失效 → 运行期由 `conanrun` 环境提供 `LD_LIBRARY_PATH`。
4. `make -j>1` 在本环境报 jobserver mkfifo 错误 → 使用 `-j1`。
5. 无 X11 依赖（v2.5 默认走 Qt5 的 `conf4.*` 路径，Qt3 遗留路径不启用）。

## 依赖关系

- **编译依赖**: qt5-qtbase/5.15.2.2（+ zlib/dbus/expat 传递）
- **运行依赖**: Qt5Core + Qt5Xml 运行库（由 Conan 依赖链提供）

## 上游测试

上游**无自动化测试套件**（无 `tests/`、无 `make check`/CTest/pytest 注册）。
验证入口 = `examples/*.qc`（4 个样例），已在本机全部实测执行（4/4 PASS）。

## 参考

- 上游: https://github.com/psi-im/qconf
- 曾用名: https://github.com/psi-plus/qconf
