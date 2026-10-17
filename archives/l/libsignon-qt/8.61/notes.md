# libsignon-qt 8.61 适配笔记

## 编译环境
- 构建系统: cmake（上游为 qmake 工程 `lib/SignOn/signon.pro`，配方经 `exports_sources` 自带 `CMakeLists.txt`）
- 编译日期: 2026-10-03
- 编译器: clang / clang++（OHOS SDK 26.0.0.18 / clang 15，aarch64-linux-ohos）
- 状态: published

## 适配背景

`libsignon-qt`（上游 signond 仓库的 `lib/SignOn` 客户端库）是 kaccounts-integration 26.04.0 依赖链的一环：
- 仓内 Qt6 KDE 栈的 kaccounts-integration 要求 `find_package(SignOnQt6 8.55 CONFIG)`，ohpcd 制品仓无任何 signon 包（仅有无关的 `libsignon-glib`）；
- 上游只发 Qt5 形态（`TARGET=signon-qt5`、`CMAKE_BASENAME=SignOnQt5`、`QT += core dbus`），无 Qt6 构建脚本；
- 本包按 Qt6 形态适配：目标 `signon-qt6`、CMake 包名 `SignOnQt6`，供下游直接消费。

## 编译步骤

```bash
# 1) 探索期（手工验证构建可行）
source .build-context-libsignon-qt-8.61
cp CMakeLists.txt SignOnQt6Config.cmake.in libsignon-qt6.pc.in <src>/
conan install --requires=qtbase/6.11.1.1 -r=ohpcd \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    -g CMakeToolchain -g CMakeDeps -of .
cmake -S <src> -B <bld> -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=<stage> \
    -DQt6_DIR=<qtbase>/lib/cmake/Qt6 -DCMAKE_PREFIX_PATH=<qtbase>
cmake --build <bld> -j1 && cmake --install <bld>

# 2) 配方验证（8 门禁）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify libsignon-qt 8.61   # Verdict: PASS
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游只有 qmake 工程，ohpcd 的 qtbase 无 OHOS mkspec，无法直接用 qmake 交叉编译 | qtbase 包未提供鸿蒙 mkspec | 自写 `CMakeLists.txt`（Qt6 形态，`find_package(Qt6 COMPONENTS Core DBus)`），经 `exports_sources` 随配方分发 |
| 2 | `find_package(Qt6)` 失败：CMakeDeps 未生成 Qt6 config | ohpcd qtbase 根 `cpp_info` 为 `cmake_find_mode=none`，CMakeDeps 直接跳过 | 配方 `generate()` 中把 `<qtbase package_folder>/lib/cmake/Qt6` 写入 `Qt6_DIR` 缓存变量（`CMakeToolchain.variables`） |
| 3 | moc 编译报 `Cannot find file SignOn/libsignoncommon.h` | 源码以 `<SignOn/xxx.h>` 互相包含（`.pri`: `INCLUDEPATH += . ..`），构建期 include 根须为 `lib/`（SignOn 的父目录） | `target_include_directories` 的 BUILD_INTERFACE 同时加入 `lib/SignOn` 与 `lib/`；INSTALL_INTERFACE 用 `include/signon-qt6` |
| 4 | `install(DIRECTORY AuthService ... )` 报路径不存在 | `AuthService`/`Identity`/`Error` 等是**无扩展名转发头文件**（各只有一行 `#include <SignOn/xxx.h>`），不是目录 | 改为 `install(FILES ...)` 装进 `include/signon-qt6/SignOn` |
| 5 | `make -j2` 报 `jobserver mkfifo: Operation not permitted` | 工作目录为 FUSE 挂载，禁 `mkfifo`（本机 E002 变体） | 统一 `-j1` 构建（`cmake --build -j1`） |
| 6 | 上游 QtTest 套件的守护进程集成路径无法执行 | 套件经 D-Bus 驱动运行中的 signond 守护进程（`testsession.conf`）；沙箱无 `dbus-daemon` 且实测不可搭建（conan dbus-daemon 静态链接 musl + 本机 /etc/passwd 无 uid 条目、FS socket bind EPERM、OHOS libQt6DBus 内置 libdbus 无会话总线地址解析） | recipe `build()` **不集成上游测试**；TestAuthSession 套件经工作区第二驱动入口逐项实跑（5 过 / 11 败 / 1 跳过 / 3 阻塞，测试源码零改动，见 `reports/test-report.md`），失败项均为守护进程依赖 |

## 源码修改

无补丁。`patches/` 为空、`patches_applied: []`。配方通过 `exports_sources` 额外分发 3 个自写构建文件（属配方资产，非上游源码改动）：

1. `CMakeLists.txt`（140 行）— 复刻 `libsignon-qt.pri` 的 SOURCES/HEADERS/INSTALLS 语义，Qt6 形态
2. `SignOnQt6Config.cmake.in` — 复刻上游 `SignOnQt5Config.cmake.in` 的变量契约（`SIGNONQT_INCLUDE_DIRS` / `SIGNONQT_LIBRARIES` / `SIGNONQT_LIBRARIES_STATIC`），并 `find_dependency(Qt6 COMPONENTS Core DBus)`
3. `libsignon-qt6.pc.in` — pkg-config 描述文件

## 依赖版本

- `qtbase/6.11.1.1`（ohpcd 已发布；提供 Qt6 Core/DBus，Qt6 CMake 包位于包内 `lib/cmake/Qt6`）

## 验证结果

```bash
$ python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify libsignon-qt 8.61
✅ 配方验证通过: libsignon-qt 8.61   →  可标记 status: published
# G0 PASS / G1 PASS / G2 PASS(conan create 干净构建 + test_package) / G3 PASS / G4 PASS / L2·L4·L5 PASS
# 报告: archives/l/libsignon-qt/8.61/reports/conan-verify-report.md

# 探索期手工构建 + 安装
$ cmake --build <bld> -j1        # rc=0
$ cmake --install <bld>          # rc=0 → include/signon-qt6/{SignOn,SignOn/*.h,SignOn/*} + lib/libsignon-qt6.a + lib/cmake/SignOnQt6/ + lib/pkgconfig/libsignon-qt6.pc

# 上游测试套件实跑（R51，2026-10-10 补测）
$ ./libsignon-qt-tests -o log.txt,txt                  # SsoTestClient 集成路径：initTestCase 需运行中 signond，Totals: 1 passed, 1 failed，rc=139
$ ./libsignon-qt-authsession-tests -o log.txt,txt      # TestAuthSession 第二驱动入口：5 过 / 11 败 / 1 跳过 / 3 阻塞（逐项明细见 reports/test-report.md）
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libsignon-qt6.a` | 客户端库（静态，`shared=True` 时构建 `.so`） |
| `include/signon-qt6/SignOn/*.h` | 公开头（9 个）与私有头 |
| `include/signon-qt6/SignOn/{AuthService,AuthSession,Error,Identity,IdentityInfo,SecurityContext,SessionData}` | 无扩展名转发头（下游 `#include <SignOn/Identity>` 用） |
| `lib/cmake/SignOnQt6/{SignOnQt6Config.cmake,SignOnQt6Targets.cmake,...}` | CMake 包（下游 `find_package(SignOnQt6 CONFIG)`） |
| `lib/pkgconfig/libsignon-qt6.pc` | pkg-config 描述 |

## 注意事项

- **CMake 包名与库名不一致是有意为之**：包名 `SignOnQt6`、目标 `SignOnQt6::SignOnQt6`、库文件 `libsignon-qt6.a`（沿用上游 `SignOnQt5` / `libsignon-qt5` 的命名习惯，仅把 5 换成 6）。
- **消费侧须先 `find_package(Qt6 CONFIG)`**：本仓库 qtbase 的 `cmake_find_mode=none` 使 CMakeDeps 不产出 Qt6 config，`Qt6_DIR` 需由消费侧（或 Conan `CMakeToolchain.variables`）显式指定，否则 `SignOnQt6Config.cmake` 里的 `find_dependency(Qt6)` 会失败。`test_package/` 已示范该写法。
- **本包不含 signond 守护进程**：上游 `server/`（signond 自身）与 `src/`（插件）不在本包范围；纯客户端库消费无需守护进程即可编译链接，仅运行时需要。
- **上游测试不可在 CI 内跑，本地已按 R51 实跑并如实回填**：套件的守护进程集成路径依赖运行中的 signond + 会话总线（CI 容器同样没有），未集成进 `build()`；TestAuthSession 套件经工作区第二驱动入口逐项实跑（5 过 / 11 败 / 1 跳过 / 3 阻塞，失败项均为守护进程依赖）；`test_package`（20 处断言，纯值类型 API，无需 D-Bus）承担 CI 回归职责。
---

**编译结束**: 2026-10-03 11:26
**最终状态**: published
