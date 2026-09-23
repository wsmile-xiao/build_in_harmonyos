# liborigin

读取 OriginLab 项目文件（`.opj`）的 C++ 库：解析 Origin 3.5 ~ 2022b 各版本工程中的
工作簿（数据表）、矩阵、图形、函数、笔记与 Excel 表，并提供 `opj2dat` 命令行工具把
工作簿数据导出为 ASCII `.dat`。

- 上游：Stefan Gerlach 维护的独立版 liborigin（GitHub `gerlachs/liborigin`，GPL-3.0-or-later），
  源自 SourceForge/SciDAVis 版 liborigin 并修复了大量未初始化 POD 引发的 UBSan 告警。
- 本仓库当前版本：`3.0.4`。

## 功能概述

- `OriginFile` 类：打开并解析 `.opj`，暴露 `version()`、`spreadCount()/spread()`、
  `matrixCount()/matrix()`、`graphCount()/graph()`、`functionCount()`、`noteCount()`、
  `excelCount()`、`datasetCount()/dataset()`、`project()` 等项目结构。
- `liboriginVersion()/liboriginVersionString()` 等版本查询 API。
- `opj2dat`：`opj2dat [--check-only] <file.opj>`，把每个工作簿导出为 `<file.opj>.<n>.dat`
  （缺测值按 NaN 落盘）。
- 自带 `liborigin.pc`（本仓库配方改为由 Conan 生成等价元数据）与 CMake 安装规则。

## OHOS 适配

- **平台识别与 SONAME**：os=OHOS 时 Conan 默认将 `CMAKE_SYSTEM_NAME` 设为 `HarmonyOS`，
  而 OHOS SDK 的 CMake 只有 `Modules/Platform/OHOS.cmake`（内容为 `include(Platform/Linux)`）。
  名字对不上时 CMake 只打印 "System is unknown to cmake" 继续，平台变量留空，
  共享库失去 `-Wl,-soname` 与版本软链。配方显式设 `cmake_system_name=OHOS`，
  实测产物 `liborigin.so.3.0.4` + `liborigin.so.3` + `liborigin.so` 软链齐全、
  `DT_SONAME=liborigin.so.3`。
- **静态/动态二选一**：上游默认同时构建静态库与动态库（同名安装）。配方用 Conan
  `shared` 选项映射 `BUILD_SHARED_LIBS` / `BUILD_STATIC_LIBS`，默认静态
  （`bin/opj2dat` 因此自带实现、无需运行时库路径）；`-o shared=True` 亦可，
  共享 flavor 的消费方按 Conan 惯例经 runenv 提供 `LD_LIBRARY_PATH`。
- **ELF 签名**：OHOS 要求 ELF 带有效 `.codesign` 才能执行/加载。安装阶段 CMake 会清除
  可执行文件的构建期 RUNPATH，字节变化使原签名失效（共享版 `bin/opj2dat` 实测直接
  执行报 `Operation not permitted`，rc=126）。配方在 `package()` 中对包内 ELF
  去旧签名段后重新自签名。
- **文档目标**：上游 `find_package(Doxygen)` 命中时会向 `ALL` 添加 doc 目标，
  配方以 `CMAKE_DISABLE_FIND_PACKAGE_Doxygen=ON` 关闭，保证构建机差异不影响结果。
- **公共 API 修复**：上游 3.0.4 头文件声明 `liboriginVersionBugfix()`，实现却叫
  `liboriginVersionPatch()`，按头文件调用会在链接期报 undefined symbol；配方
  补丁 0001 改名对齐（上游 master 仍存在该不一致）。
- **上游回归夹具**：`tests/examples/*.out.orig` 在 3.0.4 标签内仍打印 `opj2dat 3.0.3`
  版本横幅，上游脚本对整份 stdout 做 diff 因而必然失败；上游 master 提交
  `2ab0436 tests: fix version in reference output`（2026-07-28）已自行修复同一问题，
  配方补丁 0002-0005 与该修复一致（逐文件 1 行）。

## 依赖关系

- 编译依赖：无第三方库（C++17 标准库；`tree.hh`、`endianfstream.hh` 为源码自带）。
- 运行依赖：无（静态 flavor 的 `opj2dat` 自包含；共享 flavor 需 Conan runenv 提供库路径）。

## 产物

| 路径 | 说明 |
| --- | --- |
| `lib/liborigin.a`（默认）或 `lib/liborigin.so.3.0.4`（`-o shared=True`） | 解析库 |
| `include/liborigin/{OriginFile,OriginObj,OriginParser}.h`、`tree.hh` | 公共头文件 |
| `bin/opj2dat` | `.opj` 数据导出工具 |
| `licenses/COPYING` | GPL-3.0 许可证文本 |

## 参考资料

- 上游仓库：<https://github.com/gerlachs/liborigin>
- 相关项目：Ropj（<https://github.com/aitap/Ropj>）、openopj（<https://github.com/jgonera/openopj>）
