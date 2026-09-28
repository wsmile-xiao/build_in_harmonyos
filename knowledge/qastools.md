# qastools 1.4.0 — 知识扩展（召回结果 + 适配记录）

- 生成时间：2026-09-19
- 目标库：qastools/1.4.0（Qt6 系 ALSA 图形工具集：qasmixer / qashctl / qasconfig）
- 上游仓库：https://gitlab.com/sebholt/qastools（v1.4.0 tag）

## 1. 检索键

| 键 | 值 |
| --- | --- |
| 库名/领域词 | qastools, Qt6, qtbase, alsa, udev, CMake |
| trigger_tool | conan / cmake / find_package |
| phase | configure / consume / build |
| 报错原文 | `libudev.h file not found`；`Failed to find required Qt component "LinguistTools"`；`ld.lld: error: unable to find library -ludev`；`undefined symbol: udev_new` |

## 2. 知识图谱命中条目（逐条已读）

### E323 — Qt6DBus 不可消费修复（qtbase 6.11.1 案例）
- `knowledge/graph/E323.kv` + `knowledge/doc/E323.md`
- 命中：qasmixer 链接 `Qt6::DBus`，同一问题域。
- 结论：必须选用 qtbase 的 dbus 变体（qtbase-sql-dbus/6.11.1）；裸 qtbase/6.11.1 的 FEATURE_dbus=OFF 会让 Qt6Config.cmake 直接置 Qt6_FOUND=FALSE。

### E441 — qtbase 变体先例（Qt6Sql/Qt6DBus 缺失）
- 命中：Qt6 组件 REQUIRED 失败 → 选用已发布的 qtbase 变体包。
- 结论：`qtbase-sql-dbus/6.11.1` 同时提供 sql + dbus。

### E438 — OHOS 上 CMake 消费 Qt6 的标准做法
- `Qt6_DIR=qtbase 包 lib/cmake/Qt6`、`QT_QMAKE_TARGET_MKSPEC=harmonyos-clang`、`CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=BOTH`。
- 结论：qastools 的 conanfile `generate()` 按此模板桥接 Qt6Config.cmake / Qt6SvgConfig.cmake。

### E091 — linux/netlink.h 与 musl sockaddr_storage 重定义
- 适用性：qastools 源码**未直接 include** linux/netlink.h（已 grep 确认）；udev 监听走 libudev 的 netlink 封装，风险在 libudev 库内部，不在 qastools 编译单元。记录备查，不预判。

### E237 — 运行期事件源探测降级（acpid 案例）
- 适用：udev sound 卡热插拔在 OHOS 上无 udev 守护进程，`udev_monitor_new_from_netlink` 可能失败。
- 结论：源码已有 NULL 降级分支（udev_device_lookout.cpp），不需要额外 patch；notes 中声明运行期限制。

## 3. 非条目知识

- `knowledge/operations/`：无 qastools 专门条目；Qt6 消费通用做法见 E438。
- 同库归档：qastools 无历史归档（首次适配）。
- `knowledge/requirements/R*.kv`：无 qastools 相关条目。

## 4. 同类 PR 横向扫描

- 目标仓库全库 grep `qastools`：0 命中 → 无现成 PR/Issue 可复用。

## 5. 本次适配踩坑记录

| 错误原文 | 根因 | 修复 |
| --- | --- | --- |
| `Failed to find required Qt component "LinguistTools"` | 制品仓所有已发布 qtbase 变体均不含 Qt6LinguistTools | patch 0001：`FIND_PACKAGE(Qt6 QUIET COMPONENTS LinguistTools)`，缺失时跳过 i18n 子目录（翻译运行时加载，跳过安全） |
| `Could NOT find Qt6Svg (missing: Qt6Svg_DIR)` | qtbase 与 qtsvg 分属两个包，CMAKE_PREFIX_PATH 未含 qtsvg 包目录 | conanfile `generate()` 同时把 qtbase 与 qtsvg 包目录加入 CMAKE_PREFIX_PATH，并显式设 `Qt6_DIR` / `Qt6Svg_DIR` 缓存变量 |
| `fatal error: 'libudev.h' file not found` | 子目录 CMakeLists 的 `INCLUDE_DIRECTORIES` 未继承顶层 | patch 0002：在顶层 CMakeLists PROJECT() 后注入 `INCLUDE_DIRECTORIES(${UDEV_INCLUDE_DIRS} ${ALSA_INCLUDE_DIRS})`（conanfile 通过 CMAKE cache 传入绝对路径） |
| `ld.lld: error: undefined symbol: udev_new` | 子目录 `SET(UDEV_LIBRARIES udev)` 覆盖顶层缓存变量，且 -ludev 在 HMDFS 上无搜索路径 | conanfile 改用 `UDEV_LIBRARIES_CACHE`（绝对路径 libudev.a）；patch 0004/0005 在子目录把该值转回 `UDEV_LIBRARIES` |
| `implicit instantiation of undefined template 'std::basic_ostringstream<char>'` | musl/libc++ 下 sstream 未隐式包含 | patch 0003：states_db.cpp 显式 `#include <sstream>` |
| `PermissionError: Operation not permitted: .../bin/qasmixer` | HMDFS 不可执行 conan 缓存中的二进制 | test_package 改为 ELF magic + NEEDED 表静态校验，不实际执行 GUI 二进制 |

## 6. 适配要点汇总

1. 依赖闭包（强制）：qtbase-sql-dbus/6.11.1（Core/Widgets/Network/DBus）、qtsvg/6.11.1（Svg）、alsa-lib/1.2.16.1、libudev-zero/1.0.4。
2. 构建系统：CMake ≥3.25；`FIND_PACKAGE(UnixCommands REQUIRED)` 在本 CI 可解析（bash 存在），无需 Gentoo 式规避。
3. 上游无自动化测试（CTest 0 个、测试入口 0 个）→ 按提示词口径：展示真实测试入口（无），test_package 单独汇报（TP-001..006）。
4. 源码 URL：https://gitlab.com/sebholt/qastools/-/archive/v1.4.0/qastools-v1.4.0.tar.gz，sha256 `c2c06a07741b39be65744afef9b8e53708e7c3e937cd70df65e13cf2c937c5cc`。
5. udev 运行期限制：OHOS 无 udev 守护进程，sound 卡热插拔监听不会工作（源码 NULL 降级分支保证进程不崩溃）。
