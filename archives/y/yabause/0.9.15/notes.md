# yabause 0.9.15 适配笔记（OpenHarmony PC / aarch64，模式B探索性编译）

## 编译环境
- 构建系统: CMake（上游为 CMake，非 autotools；init-build 上下文中 BUILD_SYSTEM=autotools 为误标，以 CMakeLists.txt 为准）
- 编译日期: 2026-10-04
- 编译器: clang 15.0.4 / clang++ 15.0.4（OHOS SDK 26.0.0.18 sysroot，aarch64-linux-ohos）
- CMake: 4.1.2 | make: GNU make（单进程 -j1）
- 主机: HarmonyOS HongMeng Kernel aarch64；内存硬约束 <1G 可用，全程 make -j1
- 状态: 核心库编译成功（built），上游无自动化测试

## 源码信息
- 来源: https://deb.debian.org/debian/pool/main/y/yabause/yabause_0.9.15.orig.tar.gz
- sha256: 4334c43fe0f3ff297bac8e91f4e059fe5fd276291faff2489e37b5b3a4ccc2b2（下载后核验一致，与 .tarball-sha256 匹配）

## 上游清点（R51 第一步）
- 自动化测试框架：**无**。全树无 tests/ 目录（CMakeTests/ 是 CMake find-module：FindFFmpeg/FindGLEW/FindSDL2，非测试）；无 `enable_testing()`/`add_test()` 注册（ctest 注册数 = 0）；无 `make check` 目标。
- 诊断工具：`src/tools/{cdtest.c, pertest.c}`，仅 `-DYAB_TESTS=ON` 时构建，为需硬件的 CD/外设接口诊断程序。
- 自动化测试前端：`src/runner`（跑 Saturn 自测 ROM）需要 `lodepng` 子模块（Debian orig 包未含，目录缺失，CMake 守卫直接 return）且需外部测试 ROM 文件，本环境无法构建。

## 实际编译命令
```bash
export DEFAULT_PREFIX=/storage/Users/currentUser/usr/local
export TEST_PREFIX=/storage/Users/currentUser/test-install-yabause-0.9.15
cd /storage/Users/currentUser/builds/yabause-0.9.15.work
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_C_COMPILER=clang \
  -DYAB_WANT_MPEG=OFF -DYAB_WANT_SDL=OFF -DYAB_WANT_OPENAL=OFF \
  -DYAB_WANT_OPENGL=OFF -DYAB_WANT_C68K=OFF -DYAB_WANT_MUSASHI=ON -DYAB_USE_SSF=OFF
cd build && make -j1            # MAKE_EXIT=0，产物 build/src/libyabause.a (2025382 字节)
make install                    # 无该目标：上游未注册任何 install()（见下）
```

参数说明（最少参数 + 最小依赖，R1）：
- YAB_WANT_OPENGL=OFF：OHOS sysroot 无 GL/GLES/glew 头，避免 OpenGL+FindGLEW 链。
- YAB_WANT_SDL/OPENAL/MPEG=OFF：无 SDL2/OpenAL/FFmpeg 依赖。
- YAB_WANT_C68K=OFF：其 ExternalProject(gen68k) 需额外生成器，本构建用 musashi 68k 核（M68KCORE_MUSASHI=3，编译进 m68kmusashi.c）。
- YAB_USE_SSF=OFF：不依赖 zlib。
- YAB_TESTS 保持默认 OFF：cdtest/pertest 无法在 OHOS 链接（见"上游测试实跑"）。

## 踩坑与修复
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake_minimum_required(VERSION 2.8)` 报 "Compatibility with CMake < 3.5 has been removed" | CMake 4.1.2 移除了 <3.5 兼容 | 4 个参与构建的 CMakeLists（顶层/ src/ / musashi/ / runner/）`cmake_minimum_required` 提升到 3.5，补丁 0001-0004（c68k 未启用无需处理） |
| 2 | 嵌套 ExternalProject `m68kmake`（musashi 生成器）configure 阶段同样报 CMake<3.5 错误 | ExternalProject 子项目 src/musashi/CMakeLists.txt 自身 `cmake_minimum_required(VERSION 2.6)` | 提升为 3.5（补丁 0003） |
| 3 | `make install` 无规则 | 上游库目标无 install(TARGETS)，l10n 的 `if(UNIX AND NOT APPLE)` 对 HarmonyOS 不成立 → 0 个 install() 注册，CMake 不生成 install 目标 | 记录为上游限制；交付物是静态库，conan recipe 负责安装；探索阶段不强制 DESTDIR 安装 |
| 4 | cdtest/pertest 链接失败（undefined ArchCD / PERLinuxJoy） | OHOS 落在 src/CMakeLists.txt UNKNOWN_ARCH 分支（sock-dummy/thr-dummy，无 cd-*.c / perlinuxjoy.c）；且 sysroot 无 linux/cdrom.h、linux/joystick.h，无法补编译 | 记录为上游诊断工具需硬件+平台头缺失，非默认构建内容（YAB_TESTS 默认 OFF），不强行修复 |
| 5 | src/c68k/CMakeLists.txt 补丁 dry-run 失败 | 原文件 CRLF 行尾，差异生成/回放行尾不匹配 | c68k 未启用（YAB_WANT_C68K=OFF）→ 还原源文件、撤销 0005 补丁，补丁集收敛为 0001-0004 |
| 6 | 后台 `make &` 会话被 SIGHUP 杀死 | 非交互 shell 后台进程生命周期 | 改为前台 `make -j1 > make.log`（300s 内完成） |
| 7 | `/tmp` 只读 | E002 平台限制 | 临时目录改用 `$HOME`/builds 下 scratch |

OOM 情况：构建日志 make.log 无 OOM/kill/内存不足记录；make -j1 全程稳定。

## 源码修改
补丁 4 个（archives/y/yabause/0.9.15/patches/），全部为 portability 性质（CMake 版本下限提升），无平台宏 `__OHOS__`：
- 0001-CMakeLists.txt.patch（顶层 2.8→3.5）
- 0002-src-CMakeLists.txt.patch（2.8→3.5）
- 0003-src-musashi-CMakeLists.txt.patch（2.6→3.5，m68kmake 子项目）
- 0004-src-runner-CMakeLists.txt.patch（2.8→3.5）
（c68k 子项目未启用：配方 YAB_WANT_C68K=OFF，其 CMakeLists.txt 不参与构建，原始 0005 补丁因 CRLF 行尾 difflib 补丁 dry-run 不稳定已撤销并还原源文件）
验证：对 orig 全树逐个 `patch -p1 --dry-run` 全部 OK，全量应用后目录树与 work 目录一致（仅 .edit-tracker.json 差异）。

## 依赖版本
- 无外部运行时依赖；musashi 68k 核内嵌生成（m68kmake 由 clang 原生构建）。
- 编译器工具链：clang/clang++ 15.0.4（OHOS SDK 26.0.0.18）。

## 验证结果（本机实测）
```bash
# 1) 核心库编译
make -j1   # [100%] Built target yabause, libyabause.a 2.0MB, exit 0

# 2) HarmonyOS 专用冒烟测试（headless 端口式核心表 + skip_load）
clang -O1 -o yabsmoke yabsmoke.c build/src/libyabause.a -lm -pthread
./yabsmoke
# YabauseInit -> 0
# SMOKE_OK
# exit 0  —— 初始化成功，仿真 5 帧无崩溃，DeInit 正常
```

## 上游测试实跑（R51 三步法，如实记录）
- 清点：ctest 注册 0；make check 目标不存在；tests/ 目录不存在；唯一测试程序 src/tools/{cdtest,pertest}（YAB_TESTS=ON，需硬件）。
- 实跑：
  - cdtest：链接失败（缺 ArchCD → OHOS UNKNOWN_ARCH 分支未编译 cd-*.c；sysroot 无 linux/cdrom.h）。无法生成可执行文件。
  - pertest：链接失败（`#ifdef __linux__` 引用 PERLinuxJoy，perlinuxjoy.c 因 sysroot 无 linux/joystick.h 未编译）。无法生成可执行文件。
  - runner 自动化测试：lodepng 子模块缺失 + 无测试 ROM，无法构建。
  - 无任何可运行的注册自动化测试 → 通过率按上游注册口径为 0/0；按"尝试运行的测试程序"口径为 0/2（详见 reports/test-report.md）。
- 替代验证：自建 headless 冒烟测试（YabauseInit/YabauseEmulate/YabauseDeInit）1/1 通过，作为 HarmonyOS 平台验证证据。

## 交付物
| 文件 | 说明 |
|------|------|
| build/src/libyabause.a | 核心模拟器静态库（2,025,382 字节），无前端（gtk/qt/sdl/cocoa/runner 因依赖缺失全部 return 跳过） |
| patches/0001-0004 | CMake 版本兼容补丁 4 个 |
| reports/test-report.md | 上游测试报告 |
| reports/result-summary.json | 结构化汇总 |

## 注意事项
- 前端缺口：无 SDL/GL/Qt/GTK/lodepng 时一个前端二进制都构建不出来，只有核心库。conan recipe 应把 `libyabause.a` 作为库包交付（R38：无可执行文件 → 不需要 commands.json）。
- OHOS 目标三元组：conan 配方构建时建议 CMAKE_SYSTEM_NAME=OHOS（本机原生为 HarmonyOS，UNKNOWN_ARCH 分支同样成立且最稳）。
- `make install` 不存在：conanfile.py 需自行 package lib/include（头文件从 src/ 收集，库从 build/src/libyabause.a）。
- 若后续要启用 c68k，需同时提升其 CMakeLists.txt 的 cmake_minimum_required（gen68k 生成器，因 CRLF 行尾 difflib 补丁不稳定，本版未启用）。
---

**编译结束**: 2026-10-04 22:45
**最终状态**: published
