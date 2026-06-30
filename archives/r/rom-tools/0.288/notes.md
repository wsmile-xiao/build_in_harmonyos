# rom-tools 0.288 适配笔记

## 编译环境
- 构建系统: custom (standalone Makefile, bypassing MAME's genie build system)
- 编译日期: 2026-06-04
- 编译器: clang 15.0.4 / clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built (2 CLI tools compiled successfully)

## 编译步骤
1. MAME的官方构建系统(genie)需要SDL2，在HarmonyOS上不可用
2. 创建了standalone build方案，绕过genie构建系统
3. 使用C++20编译MAME核心工具源码
4. 创建osdlib_minimal.cpp替代osdlib_unix.cpp（移除SDL依赖）
5. 跳过osdmodule.cpp（需要emu_fatalerror，CLI工具不需要动态模块加载）
6. 跳过LZMA的AesOpt.c/Sha256Opt.c（ARM crypto intrinsics不可用）

## 成功编译的工具
| 工具 | 大小 | 说明 |
|------|------|------|
| chdman | 1.8MB | CHD磁盘映像管理工具 |
| romcmp | 1.7MB | ROM比较工具 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | MAME genie构建需要SDL2 | genie.lua检测pkg-config sdl2 | 绕过genie，创建standalone Makefile |
| 2 | osdlib_unix.cpp包含SDL2/SDL3头文件 | clipboard函数依赖SDL | 创建osdlib_minimal.cpp，stub clipboard函数 |
| 3 | `-m64` flag用于arm64 | MAME构建系统假设64=config64 | standalone构建不使用genie生成的Makefile |
| 4 | std::string_view/std::span/char8_t缺失 | C++17不支持 | 升级到C++20 |
| 5 | LZMA ARM crypto intrinsics不可用 | clang 15不支持armv8-a+crypto | 跳过AesOpt.c/Sha256Opt.c，使用基础实现 |
| 6 | emu_fatalerror依赖emu.h | osdmodule.cpp引用emucore.h | 不编译osdmodule.cpp，CLI工具不需要 |

## 源码修改
- .standalone-build/osdlib_minimal.cpp: 新建，替代osdlib_unix.cpp（移除SDL依赖）

## 依赖版本
- zlib: 1.3.1 (预编译包)
- expat: 2.7.1 (预编译包)  
- FLAC: 1.4.3 (预编译包)
- zstd: 1.5.6 (预编译包)
- utf8proc: 2.11.3 (预编译包)
- LZMA: 内嵌3rdparty版本

## 验证结果

```bash
$ chdman --help
chdman - MAME Compressed Hunks of Data (CHD) manager 0.288 (unknown)
Usage: chdman info/verify/createraw/createhd/createcd/createdvd/createld/extractraw/extracthd/extractcd/extractdvd/extractld/copy/addmeta/delmeta/dumpmeta

$ romcmp
usage: romcmp [-d] [-h] [dir1 | zip1] [dir2 | zip2]
```

## 注意事项
- 不能编译完整MAME模拟器（需要SDL2/X11/fontconfig等图形依赖）
- chdman和romcmp是独立CLI工具，不依赖SDL
- 构建使用C++20（MAME 0.288要求C++17，但language.h使用char8_t需要C++20）
---

**编译结束**: 2026-06-04 11:03
**最终状态**: built
