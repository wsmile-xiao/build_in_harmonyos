# ttylog 0.31 OpenHarmony PC aarch64 适配笔记

## 来源与依赖
- 官方仓库：`https://git.code.sf.net/p/ttylog/code`；官方发布：`https://sourceforge.net/projects/ttylog/files/ttylog/0.31/ttylog-0.31.tar.gz/download`。
- SHA256：`127e2e1bebd19b532067f658e794c12c6dfb256bf0110be58a1c96fc442c1096`。
- GPL-2.0-or-later；只有系统 libc / termios，Conan 依赖为零。上游源码为 C；源码包 CMakeLists.txt 包含两个 CTest 项。
- G2 曾报 `BadZipFile: File is not a zip file`：SourceForge `/download` 末段无扩展名，Conan `get()` 错判格式；知识图谱 **E483** 命中，在 `get(..., filename="ttylog-0.31.tar.gz")` 指定文件名。G1 无补丁配方仍要求 `export_sources()`/`apply_conandata_patches()`；补齐这两个调用。
- 2026-09-24，x86_64 runner 交叉到 OHOS armv8，NDK clang 15.0.4 / CMake 3.28.2 / Conan 2.29.1。

## 编译
- `init-build` 将项目误判为 autotools；以实际 `CMakeLists.txt` 为准，配方使用 CMakeToolchain / CMake。
- 手工验证：NDK clang + `cmake -S ... -B ... -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang`，随后 `cmake --build ...` 成功，产物为 AArch64 ELF。
- 上游 CMake 在 Unix 上链接 `rt`；无补丁。交付 OHOS 包以 `CMAKE_EXE_LINKER_FLAGS=-static` 链接，避免 x86 runner 缺 `/lib/ld-musl-aarch64.so.1` 而无法实际执行验证；产物安装至包内 `bin/ttylog`。此处未使用系统外依赖。

## 上游测试清点与验证（R51）
- 源码归档没有 `tests/` 子目录（0 个），无 pytest；`CMakeLists.txt` 第 40–43 行注册两个 CTest：`ttylogRuns`（无参→`no params.`）和 `ttylogHelp`（`-h`→`Usage:`）。合计 2 项。
- 最初动态构建产物在本机缺 OHOS musl loader，不能直接用 QEMU 执行；**未把动态产物记为实跑通过**。
- 用上述同源 `ttylog.c.o` 静态重链副本，经 `qemu-aarch64 ttylog-static` 和 `qemu-aarch64 ttylog-static -h` 实跑，上游两项原断言 **2/2 通过**（100%）。`-v` 同样可运行。最终配方交付静态版本，test_package 会对**交付的**包内 CLI 逐项实跑，而不是只执行测试替身。
- 不测试实际物理串口采集：x86 runner 无 OHOS 串口设备；CLI 参数解析与错误路径覆盖由 test_package 提供。

## 本地测试与可移植性
- `test_package/test_ttylog.py` 验证交付产物无参、`--help`、`--version`、设备错误路径，4/4；若 CI 不提供 qemu-aarch64 则明确报告 SKIP，不声称运行通过。
- 上游测试未修改；没有源码补丁。`init-build` 的 `.orig`/`.work` 初始为硬链接，已经在构建前断开，以保护上游基线。
---

**编译结束**: 2026-09-24 19:50
**最终状态**: built
