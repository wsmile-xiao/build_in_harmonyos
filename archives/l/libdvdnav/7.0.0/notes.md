# libdvdnav 7.0.0 适配笔记

## 软件概述

**libdvdnav** 是 VideoLAN 的 DVD 导航库，封装 DVD 虚拟机与播放状态，
对外提供单一逻辑块流 + dvdnav 事件，支持 DVD 菜单、多角度回放与交互式 DVD。
入口 API：`dvdnav_open()` / `dvdnav_get_next_block()` / `dvdnav_close()` 等。

- **上游版本**：7.0.0
- **上游仓库**：https://code.videolan.org/videolan/libdvdnav
- **官方源**：https://download.videolan.org/pub/videolan/libdvdnav/7.0.0/
- **许可证**：GPL-2.0-or-later
- **构建系统**：meson（`meson.build` + `meson_options.txt`），非 autotools

## 构建系统分析

- 顶层 `meson.build`：`project('libdvdnav', 'c', version: '7.0.0', ...)`
- C 标准为 c17，`default_library=both`
- 子目录：`src/`（库源码）、`src/dvdnav/`（API 头 + version.h.in）、`examples/`、`doc/`
- 关键依赖：
  - `dependency('dvdread', version: '>=6.0.0', fallback: 'libdvdread')`
  - `dependency('threads')`（windows/cygwin/android 除外）
- 官方 `.gitlab-ci.yml` 通过 `git clone ... subprojects/libdvdread` 提供 fallback 子项目，
  本配方按同样做法 vendoring libdvdread 源码到 `subprojects/libdvdread/`。

## 依赖链与发布状态（W0/R36）

| 依赖 | 关系 | 仓库归档 | 处理 |
|------|------|---------|------|
| libdvdread | meson fallback 子项目 | 无 | vendoring libdvdread 7.1.1 源码 |
| pthread | 系统库 | — | `cpp_info.system_libs` |
| libdvdcss | 可选直链（dvdread 侧） | 无（libdvdcss 1.5.0 在 l/） | 默认禁用直链，dvdread 通过 dlfcn 动态探测 |

- libdvdread 不在 build_in_harmonyos 归档中，按官方 CI 做法 vendoring 源码。
- libdvdread 7.1.1 的 meson 默认 `libdvdcss=auto`，找不到 pkg-config 时回退 dlfcn 动态探测。
  OHOS 提供 `dlfcn.h` 与 `dlopen`，故 `with_dvdcss=false` 可正常编译。

## 上游测试套件审计（W3/TEST_QUALITY_SPEC）

逐项审计上游 7.0.0 tarball 与官方 CI：

1. `meson.build` 无 `test(...)` / `benchmark(...)` 调用。
2. `examples/menus.c` 是命令行示例程序，非测试（需 DVD 设备实参）。
3. `.gitlab-ci.yml` 各 job 仅执行 `meson setup build` + `meson compile -C build`，
   无 `meson test` / `ninja test` / `ctest`。
4. tarball 无 `test/`、`tests/`、`check/` 目录，无 `*.test`、`*.spec` 测试文件。
5. `doc/` 仅为 Doxygen 文档配置，不含可执行测试。

**结论**：libdvdnav 7.0.0 上游**不存在**任何测试用例（单元/集成/其他）。
test_package 自建真实调用 libdvdnav API 的最小验证程序（见 test_package/）。

## 适配要点

- `wrap_mode=nodownload`：所有外部源（libdvdread）由 conandata 提供，禁止 meson 联网下 wrap。
- `enable_examples=false` / `enable_docs=false`：避免无关产物与额外依赖（doxygen）。
- R26 系统同名库：libdvdnav 为非系统同名库，默认 `shared=false` 静态。
- 头文件布局：`include/dvdnav/`（dvdnav.h / dvdnav_events.h / dvd_types.h / version.h），
  `cpp_info.includedirs` 同时包含 `include` 与 `include/dvdnav` 以兼容 `#include <dvdnav/dvdnav.h>`。

## 验证结果

- 编译状态：通过（在 HarmonyOS aarch64 环境实测）
- 上游测试用例通过率：0/0（上游无测试套件，见「上游测试套件审计」）
- 新增测试用例通过率：1/1（test_package 真实调用 `dvdnav_version()` / `dvdnav_open(NULL)` 等 API）

## 已知限制 / TODO

- libdvdread 以 vendored 源码内嵌构建（与官方 CI 一致）；若未来 libdvdread 进入归档，
  可改为 Conan `requires`。
- `with_dvdcss` 当前仅控制顶层 libdvdnav 对 dvdread 的 dvdcss 直链选项；
  dvdread 侧 dvdcss 仍走 dlfcn 动态探测（默认行为，未额外适配）。
- 真机预检在 HarmonyOS aarch64 环境实测；CI 侧由官方 Buildbot worker 复核。
