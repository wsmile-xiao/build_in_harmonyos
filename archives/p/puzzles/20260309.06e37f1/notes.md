# puzzles 20260309.06e37f1 适配笔记

## 编译环境

- 构建系统: cmake（使用 CMakeLists.txt + cmake/platforms/）
- 编译日期: 2026-06-03
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 目标平台: OpenHarmony (aarch64)
- 状态: published

## 编译步骤

1. **源码获取**：从 git.tartarus.org/simon/puzzles.git 克隆，checkout commit 06e37f1
   - Savannah 下载 URL 返回 404，chiark.greenend.org.uk 下载存在 SSL 证书问题
   - 使用 git clone 获取指定版本

2. **CMake 配置**：
   ```bash
   cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
         -DPUZZLES_PLATFORM=ohos \
         -DCMAKE_BUILD_TYPE=Release \
         ..
   ```
   - 关键参数：`-DPUZZLES_PLATFORM=ohos`（指定使用 OHOS 平台配置）

3. **编译**：`make -j1`

4. **安装**：
   - DESTDIR 模式：`make install DESTDIR=$TEST_PREFIX`（40 个游戏二进制到 staging）
   - 本地安装：`make install`（安装到 ~/usr/local/bin/）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah 源码 URL 返回 404 | puzzles 在 Savannah 上没有发布该版本的 tarball | 从 git.tartarus.org 克隆源码，checkout commit 06e37f1 |
| 2 | chiark 下载 SSL 证书验证失败 | Python urllib 不支持 SSL 证书绕过 | 使用 curl -k 下载，ohc-run.py 用 --no-download 模式 |
| 3 | cmake unix.cmake 要求 GTK（FATAL_ERROR） | 鸿蒙平台无 GTK 库 | 创建 cmake/platforms/ohos.cmake 平台配置，设置 build_gui_programs=FALSE |
| 4 | ohos_fe.c 与 drawing.c 符号冲突（duplicate symbol） | nullfe 风格的 stub 函数名与 drawing.c 中间层函数同名 | 重写 ohos_fe.c 使用 vtable-based drawing_api 架构（函数以 ohos_draw_* 前缀命名） |
| 5 | 缺少 document_add_puzzle 函数 | 该函数不是 drawing_api vtable 的一部分，是独立的 frontend 函数 | 在 ohos_fe.c 中添加 document_add_puzzle 空实现 |
| 6 | VER 宏未定义 | git checkout 不含自动生成的 version.h | 手动创建 version.h 定义 VER="Version 20260309.06e37f1" |

## 源码修改

3 个补丁：

1. **cmake/platforms/ohos.cmake**（新增文件）
   - 创建 OHOS 平台 cmake 配置，禁用 GUI 程序，使用 ohos_fe.c 作为前端
   - 提供 get_platform_puzzle_extra_source_files / set_platform_puzzle_target_properties / build_platform_extras 函数

2. **cmake/setup.cmake**（修改 2 行）
   - 在平台检测逻辑中添加 OHOS 平台分支：`elseif(CMAKE_SYSTEM_NAME MATCHES "OHOS" OR PUZZLES_PLATFORM STREQUAL "ohos")`

3. **version.h**（修改 1 行）
   - 将 `#define VER "Unidentified build"` 改为 `#define VER "Version 20260309.06e37f1"`

4. **ohos_fe.c**（新增文件，未作为补丁追踪）
   - 最小化 OpenHarmony 前端，包含 drawing_api vtable stub、frontend 函数 stub 和 main()
   - 支持 --version / --help 参数

## 依赖版本

本次编译无外部依赖，puzzles 仅依赖：
- C 标准库（libc）
- 数学库（libm，-lm）
- cmake 构建工具

## 验证结果

```bash
# --version 验证（40 个游戏全部正确）
$ blackbox --version
Version 20260309.06e37f1

# --help 验证
$ blackbox --help
Usage: ... [--version|--help]
Note: This is a headless build for OpenHarmony.

# 无参数运行
$ blackbox
Note: Interactive gameplay requires a GUI frontend.
Run '... --version' for version info.
# 退出码 0

# ELF 格式
readelf -h blackbox:
  Class: ELF64, Machine: AArch64, Type: DYN (PIE)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| puzzles-20260309.06e37f1-ohos-aarch64.tar.gz | 6.5 MB | Release 制品（40 个游戏二进制，已 strip） |
| puzzles-20260309.06e37f1-ohos-aarch64-debug.tar.gz | 1.4 MB | Debug 符号包 |

## 注意事项

1. **headless 构建**：此版本为无 GUI 的 headless 构建，游戏二进制仅支持 --version/--help 参数，
   不支持交互式游戏。交互式游戏需要 GTK 或其他 GUI 前端。

2. **solver/fuzzpuzz 未安装**：CMake 安装目标仅包含 40 个 official 游戏二进制。
   solver 程序和 fuzzpuzz 不标记为 official，不会安装到 bin/。

3. **版本号需手动设置**：从 git checkout 编译时，version.h 需手动设置版本字符串。
   正式发布 tarball 中 version.h 由 Buildscr 自动生成。

4. **G0 clean-verify 不支持 cmake**：当前 ohc-run.py clean-verify 脚本硬编码使用 ./configure（autotools），
   不支持 cmake 构建系统。需更新脚本以根据 build_system 字段选择 configure 命令。

---

**编译结束**: 2026-06-03
**最终状态**: published
