# libproperties

纯 C 实现的 `.properties`（属性文件）解析库：按 `PROPERTIES_SOURCE_READ` 回调驱动的
流式解析器，逐条把 key/value 交给 `PROPERTYS_HANDLER` 回调；自带文件源
（`properties_source_file_read`）与字符串源（`properties_source_string_read`）两种读取实现。
上游同时发布 qmake（`libproperties.pro/.pri`）与 CMake 两套构建入口，本仓库采用 **CMake**。

- 上游：https://github.com/tinyhubs/libproperties
- 许可证：Apache-2.0（上游 `LICENSE` 全文为 Apache License 2.0）
- 构建系统：CMake（`cmake_minimum_required(VERSION 3.15)`）
- 依赖：**无**（只编 `buf.c` + `properties.c`，产物 `DT_NEEDED` 仅 `libc.so`）

## 功能概述

- `properties_parse()` — 解析入口，支持注释行（`#` / `!`）、折行、转义、key/value 分隔符
  （`:`、`=`、空白）与前后空白剥离
- `properties_source_file_read()` / `properties_source_string_read()` — 两种输入源实现
- 安装面：`lib/libproperties.so{,.1,.1.1.2}`（或 `libproperties.a`）+ `include/properties.h`
  + `lib/cmake/libproperties-config.cmake`
- 无命令行工具（纯库包，不生成 `commands.json`）

## OHOS 适配要点（跨版本通用）

- **平台模块缺失 → 必须同时补两件事**：本机与 CI 的 CMake 都把 `CMAKE_SYSTEM_NAME` 认作
  `HarmonyOS`，但安装里没有 `Modules/Platform/HarmonyOS.cmake`，于是
  `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 与 rpath 族链接旗标**双双未定义**：
  ① 共享库缺 `DT_SONAME`，且 CMake 连版本化文件名都不生成（安装树只剩裸 `libproperties.so`，
  W3 报 `L5a: 缺少 DT_SONAME`）——在 `generate()` 注入
  `tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"`；
  ② `CMAKE_BUILD_RPATH` 实测为**静默 no-op**（`readelf -d` 的 RPATH/RUNPATH 计数恒为 0），
  构建树内 `ctest` 会报 `Error loading shared library libproperties.so.1`——在 `build()`
  跑测试前把构建树目录前置进本次进程的 `LD_LIBRARY_PATH`（作用域仅限该条测试命令）。
- 上游测试由 `CMakeLists.txt` 里 `file(GLOB test/*.properties)` 逐文件 `add_test()` 注册，
  **N = 2**；测试与库一起构建，`libproperties_test` 没有 `install()` 规则、不进交付面。
- 上游 `CMakeLists.txt` 的 `install(EXPORT … DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/${PROJECTNAME}")`
  中 `${PROJECTNAME}` 未定义（应为 `${PROJECT_NAME}`），配置文件落在 `lib/cmake/` 而非
  `lib/cmake/libproperties/`；两条路径都在 CMake config 搜索面内，实测 `find_package(libproperties)`
  正常。属上游小瑕疵，**未修改上游文件**。
- 上游 `build.sh` 的 shebang 是 `#!/usr/bin/bash` 且用 bash 语法；本配方直接驱动 CMake、
  不调用 `build.sh`，不涉及设备缺 `/bin/bash` 的缺口。

## 使用方法

安装预编译包：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libproperties 1.1.2
```

CMake 消费者：

```cmake
find_package(libproperties REQUIRED)
target_link_libraries(your_target libproperties::libproperties)
```

## 已编译版本

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| 1.1.2 | built | 2026-09-25 | 首个移植版本；源为 tag `1.1.2` 的 codeload zip |

## 参考资料

- 源码仓库：https://github.com/tinyhubs/libproperties
- 版本级适配笔记与验证数据：`1.1.2/notes.md`、`1.1.2/reports/`
