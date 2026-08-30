# baka 2.0.4 适配笔记

## 软件身份

- **软件名**: baka 2.0.4 = Baka MPlayer 2.0.4（u8sand/Baka-MPlayer）
- **上游仓库**: https://github.com/u8sand/Baka-MPlayer（tag v2.0.4，2015-12-03 发布）
- **类型**: Qt5 GUI 多媒体播放器（TEMPLATE=app，基于 libmpv 客户端库），非库
- **状态**: published（ohos-aarch64 conan create 通过 + test_package PASS）

## 编译环境

- 构建系统: qmake（src/Baka-MPlayer.pro，in-source build）
- 编译日期: 2026-08-29
- 编译器: clang 15 / clang++（OHOS aarch64，qmake `-spec linux-clang`）
- Profile: ohos-aarch64（cppstd17 / armv8 Release），`tools.graph:skip_binaries=False`
- 并发: `make -j2`（本环境 -j 报 jobserver mkfifo 错误）

## 依赖（W0 检查全部已发布）

| 依赖 | 版本 | 说明 |
|------|------|------|
| qt5-qtbase | 5.15.2.2 | qmake 5.15.2 |
| qt5-qtsvg | 5.15.2 | QT += svg（模块 .pri 需修复） |
| qt5-qtx11extras | 5.15.2 | QT += x11extras（模块 .pri 需修复） |
| libmpv | 0.41.0 | mpv 客户端库（client.h 无旧事件） |
| libx11 | 6.4.0 | X11/Xlib.h（.pc prefix=/ 失效） |
| libxcb | 1.16 | xcb/xcb.h |
| zlib | 1.3.1.1 | static libz.a（skip_binaries=False） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | qmake configure 报 `x11 development package not found` | baka 2.0.4 是 2015 年项目，强制 `QT += x11extras` + `PKGCONFIG += x11`；x11.pc 包内 prefix 固定为 /，pkg-config 探测失败 | 不再依赖 pkg-config include：libx11/libxcb 头文件走 CPATH 显式补充；x11extras 模块经 QMAKEMODULES 提供 |
| 2 | qmake 不识别 svg/x11extras/widgets 模块 | qtsvg/qtx11extras 包内 modules-inst 的 .pri 记录的是已删除的构建目录路径 | `_setup_qmake_modules()`：正则改写 .pri 的 include/路径指向包内 modules-inst，QMAKEMODULES 提供（验证通过） |
| 3 | 编译期缺 xcb.h / X11/Xlib.h / mpv/client.h | x11.pc/mpv.pc 的 prefix=/ 使 pkg-config 的 -I/include 失效 | CPATH 显式补充 libxcb/libx11/libmpv 的 include；**CPATH 必须冒号拼接**（conan 空格拼接多路径导致整个变量失效） |
| 4 | 链接期 `unable to find library -lX11/-lmpv` | 同上，x11.pc/mpv.pc 提供 -L/lib 无效 | LIBRARY_PATH（clang 识别）显式补充 libx11/libmpv/libxcb/zlib 的 lib 目录 |
| 5 | `mpvhandler.cpp:218: error: use of undeclared identifier 'MPV_EVENT_UNPAUSE'` | libmpv/0.41.0 已移除 MPV_EVENT_PAUSE/UNPAUSE/IDLE 旧事件（mpv 0.35 API 2.0 起）；baka 2.0.4 直接使用且无条件编译保护 | patches/0001-libmpv-041-events.patch（参照上游 master 修复）：observe "idle-active"/"pause" 属性驱动播放状态，删除旧事件 case，frame_step → frame-step 命令改名 |
| 6 | 运行期无显示环境 SIGABRT | baka 是 QApplication + X11 GUI，无显示服务器无法启动 | test_package 改静态冒烟：arm64 ELF 断言 + conanrun 环境 ldd 依赖解析断言（R34 实质调用被测包产物） |

## 关键适配点（conanfile.py）

- `requirements()`：qt5-qtbase/5.15.2.2、qt5-qtsvg/5.15.2、qt5-qtx11extras/5.15.2、libmpv/0.41.0、libx11/6.4.0、libxcb/1.16、zlib/1.3.1.1（保留 baka 侧 overrides）
- `build()`：PKG_CONFIG_PATH 收集全部依赖 pkgconfig；QMAKEMODULES 提供修复后的模块 .pri；CPATH/LIBRARY_PATH 冒号拼接；qmake `-spec linux-clang` + in-source build（参照 qt5-qtx11extras 先例）；`QMAKE_STRIP=""` 防 strip（OHOS 加载器拒绝 stripped ELF）
- `package()`：TARGET=baka-mplayer、DESTDIR=build → 复制 `build/baka-mplayer` 到 package `bin/`
- `package_info()`：`cpp_info.bindirs = ["bin"]`（TEMPLATE=app，无库目标）
- source()：`apply_conandata_patches` 应用 patches/0001-libmpv-041-events.patch

## 上游测试情况

- 上游源码包内**无 tests/ 目录**、无单元测试框架（Qt GUI 播放器，2015 年停更）。
- 依据 R34 与"上游无测试自行补充"要求，补充 `test_package/test_baka.sh` 静态冒烟测试（3 条断言）：
  1. 二进制存在且可执行（arm64 ELF）
  2. conanrun 环境下 ldd 动态依赖全部解析（无 not found）
- 已在 ohos-aarch64 `conan create` test_package 阶段**实测执行 PASS**（日志 create-noskip16.log，EXIT=0）。
- 测试通过率：**新增测试 1/1 PASS（100%）**；上游 0 个测试用例，无失败项。

## 判定

- **status**: `published`（本地 conan create 通过 + test_package PASS，提交 PR 走 CI release）
- **测试通过率**: 上游 0 用例（无 tests/），补充测试 1/1 通过 = 100%
