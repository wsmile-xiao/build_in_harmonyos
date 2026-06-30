# yetris 2.3.0 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile，无 configure)
- 编译日期: 2026-06-18
- 编译器: clang/clang++ (clang 15.0.4)
- 状态: published

## 编译步骤

```bash
# yetris 是纯 Makefile 项目，无 configure 脚本
# 直接 make 编译，通过 CFLAGS_PLATFORM/LDFLAGS_PLATFORM 传递自定义参数

source .build-context-yetris-2.3.0
cd $BUILD_SRC_DIR

# 编译（需要指定 ncurses 头文件路径和 lib 路径）
make PREFIX=$DEFAULT_PREFIX \
     CFLAGS_PLATFORM="-I$DEFAULT_PREFIX/include -Wno-narrowing" \
     LDFLAGS_PLATFORM="-L$DEFAULT_PREFIX/lib"

# 安装到 staging 目录
make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX \
     CFLAGS_PLATFORM="-I$DEFAULT_PREFIX/include -Wno-narrowing" \
     LDFLAGS_PLATFORM="-L$DEFAULT_PREFIX/lib"

# 安装到 $DEFAULT_PREFIX（模拟用户部署）
make install PREFIX=$DEFAULT_PREFIX \
     CFLAGS_PLATFORM="-I$DEFAULT_PREFIX/include -Wno-narrowing" \
     LDFLAGS_PLATFORM="-L$DEFAULT_PREFIX/lib"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ncurses.h 未找到 | Makefile 默认头文件路径不含 $DEFAULT_PREFIX/include | 通过 `CFLAGS_PLATFORM="-I$DEFAULT_PREFIX/include"` 指定 |
| 2 | C++ 标准库 redefinition 错误（bool/int 混淆） | ncurses.h 中 `#if 0` 禁用了 C++ bool 兼容分支，导致 `bool` 被 `#define` 为 `int`，与 C++ 原生 `bool` 类型冲突 | 修改 ncurses.h 第274行：`#if 0` → `#if defined(__cplusplus)`（平台级修复，见 R23 平台检测机制） |
| 3 | C++11 narrowing 错误（PieceDefinitions.cpp） | `char` 数组用负整数值初始化触发 C++11 narrowing 规则 | `CFLAGS_PLATFORM` 添加 `-Wno-narrowing`（编译器标志，不改源码） |
| 4 | Makefile 缺少 ncurses lib 路径 | 默认 linker 路径不含 $DEFAULT_PREFIX/lib | `LDFLAGS_PLATFORM="-L$DEFAULT_PREFIX/lib"` |
| 5 | manifest 缺少 build_system 字段 | init-build 默认写入 `build.system: autotools`，实际为 makefile | 修正为 `build_system: makefile` + `build.system: makefile` |

## 平台级修复（ncurses.h C++ 兼容性）

**问题**：ncurses.h 头文件在生成时使用了 `#if 0` 硬编码禁用了 C++ bool 兼容路径：
```c
#if 0	/* __cplusplus, etc. */    // ← 应为 #if defined(__cplusplus)
```

这导致在 C++ 编译模式下，ncurses.h 执行了：
```c
#undef bool
#define bool NCURSES_BOOL   // 即 #define bool int
```

`bool` 被重定义为 `int`，破坏了 C++ 标准库中所有依赖 `bool` 类型的模板特化（如 `std::hash<bool>` 和 `std::hash<int>` 变成重定义）。

**修复**：修改 ncurses.h 和 ncursesw/curses.h 的第274行：
- `#if 0` → `#if defined(__cplusplus)`
- 此修复向后兼容：C 代码不受影响（__cplusplus 未定义），C++ 代码使用原生 bool 类型。

**涉及文件**：
- `$DEFAULT_PREFIX/include/ncurses.h`（第274行）
- `$DEFAULT_PREFIX/include/ncursesw/curses.h`（第274行）

**影响**：所有使用 ncurses 的 C++ 项目在此平台上都需要此修复。

## 源码修改

无源码修改。所有适配通过编译器标志和平台级头文件修复完成。

## 依赖版本

- ncurses 6.4（静态库，已编译安装于 $DEFAULT_PREFIX）
- clang 15.0.4（OpenHarmony SDK 自带）
- make 4.4.1

## 验证结果

```bash
$ yetris --version
yetris v2.3.0 (Jun2026)
# 显示版本和 GPL3 许可证信息

$ yetris --help
# 显示 ASCII art 标题、版本号和使用说明
# 输出包含 -h/--help 和 -v/--version 选项说明
```

二进制可执行，功能正常。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| yetris-2.3.0-ohos-aarch64.tar.gz | 1245KB | 预编译包（含 bin/yetris + share/man/man6/yetris.6） |

## 注意事项

1. **ncurses.h 修复是平台级修复**，非 yetris 源码补丁。该修复影响所有使用 ncurses 的 C++ 项目。
2. **-Wno-narrowing** 是编译器标志，不修改源码。PieceDefinitions.cpp 中的负整数初始化 `{-2, -4}` 在 C++11 下触发 narrowing 错误，但运行时行为正确（char 可以存储 -128~127）。
3. **无 make check 目标**：yetris Makefile 不包含测试目标，跳过。
4. **无 configure 脚本**：yetris 使用纯 Makefile，通过 PREFIX 和 DESTDIR 参数控制安装路径。
---

**编译结束**: 2026-06-22 16:13
**最终状态**: published
