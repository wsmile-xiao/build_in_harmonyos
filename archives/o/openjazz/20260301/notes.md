# openjazz 20260301 适配笔记

## 编译环境
- 构建系统：CMake
- 编译语言：C++14
- 编译目标：OpenHarmony PC / aarch64 / clang 15
- 编译日期：2026-09-12
- 适配状态：built（待 W3 conan create 验证）

## 源码与校验
- 上游：AlisterT/openjazz
- tag：20260301
- 官方源码：`https://github.com/AlisterT/openjazz/archive/refs/tags/20260301.tar.gz`
- SHA256：`9c117a8d9aa539c4dcb3fb5788130563a83ca1d9819e538f233721d823f7a650`
- SHA256 已由本地计算、FreeBSD ports distinfo、Homebrew formula 三方核对一致。

## 适配决策
- 使用 CMake 路径；遗留 Makefile 走 SDL1.2，不采用。
- 依赖 `sdl2/2.30.10`，通过 CMakeDeps 提供 `SDL2Config.cmake` 与 `SDL2::SDL2`。
- `CMAKE_SYSTEM_NAME=Linux` 兼容上游 UNIX 分支（E092）；并行度固定为 1（R9）。
- 上游音频使用内嵌 psmplug + SDL_audio，不使用 SDL2_mixer；这是源码实证结论。
- 未添加源码补丁；所有适配通过 Conan CMakeToolchain 完成。

## 测试策略
上游没有测试框架、CTest 或 make check。test_package 只使用无头安全的纯 IO 退出路径（`-v`/`--version`/`--help`），避免触发显示初始化；共 4 项断言（二进制存在性 + 版本输出 + usage 输出）。GUI 游戏运行限制在进度与 PR 中如实说明。
