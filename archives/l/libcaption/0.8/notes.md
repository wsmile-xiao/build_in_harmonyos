# libcaption 0.8 — OHOS 适配笔记

## 上游
- 仓库: https://github.com/szatmary/libcaption
- tag: v0.8
- 源码 tarball: https://github.com/szatmary/libcaption/archive/refs/tags/v0.8.tar.gz
- SHA256: 8567765a457de43a6e834502cf42fd0622901428d9820c73495df275e01cb904
- License: MIT
- 语言: 纯 C，无外部运行时依赖

## 构建系统分析
- CMake in-tree（`cmake . && make`），无 autotools / config.guess / config.sub
- 选项:
  - `ENABLE_RE2C`（默认 OFF）：上游已提交 `src/eia608_from_utf8.c.cached`，OFF 时 CMake `configure_file` 复制为 `.c`，**无需 re2c 工具**
  - `BUILD_EXAMPLES`（默认 ON）：13 个 CLI 工具（flv2srt/ts2srt/scc2srt/...），属示例非测试，打包时关闭
- 库目标: `caption`（src/caption.c + cea708.c + eia608.c + eia608_charmap.c + eia608_from_utf8.c + mpeg.c + scc.c + srt.c + utf8.c + vtt.c + xds.c）
- 安装: `lib/libcaption.a|so` + `include/caption/*.h`

## 平台兼容性（零源码改动）
grep 全树确认无 `uname`/`config.guess`/`config.sub`/`__linux__`/`__APPLE__`/`_WIN32`/`android`/`ohos`/`harmonyos` 等平台特定代码。`caption.h` 仅对 `_MSC_VER`（Windows）补 `ssize_t` typedef，OHOS 走 POSIX 原生路径。无 pthread / dlopen / ioctl。

## 唯一补丁
`0001-CMakeLists.txt.patch`：`cmake_minimum_required(VERSION 2.8)` → `3.10`。
原因：CMake 4.x 移除 <3.5 兼容，`cmake_minimum_required(2.8)` 在 CMake 4.1.2 上直接报 `Compatibility with CMake < 3.5 has been removed`。
与 NixOS `pkgs/by-name/li/libcaption/package.nix` 的 `postPatch` 完全一致（`--replace-fail "cmake_minimum_required(VERSION 2.8)" "cmake_minimum_required(VERSION 3.10)"`）。

## 上游正式测试统计
| 测试程序 | 源文件 | CMakeLists 注册 | 媒体依赖 | 状态 |
|---|---|---|---|---|
| test_wrap | unit_tests/test_wrap.c | ✅ 未注释（唯一注册） | 无 | 正式测试 |
| eia608_test | unit_tests/eia608_test.c | ❌ 已注释 | 无 | 非正式 |
| test_captions (test_sei) | unit_tests/test_sei.c | ❌ 已注释 | argv 读媒体文件 | 非正式 |

- **正式测试数量: 1**（test_wrap，utf8 行折叠，确定性输入，exit 0）
- examples/ 13 个 CLI（flv2srt 等）= 示例，不计入正式测试
- 仓库自带 `unit_tests/tos.scc` 但无活跃测试使用（test_sei 被注释）→ 无媒体阻塞
- 无 `enable_testing`/`add_test`/`ctest` 注册 → CMake `test()` 目标 = 直接运行 test_wrap 二进制

## 消费者测试（test_package）
覆盖 CEA-608 编码/解码、parity、caption_frame 读写、控制命令往返，共 12 项确定性断言。
