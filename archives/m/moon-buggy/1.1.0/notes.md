# Adaptation Notes — moon-buggy 1.1.0

## Software
- **Name**: moon-buggy
- **Version**: 1.1.0
- **Description**: Drive some car across the moon - a simple character graphics game
- **License**: GPL-2.0-or-later OR GPL-3.0-or-later
- **Source**: https://www.seehuhn.de/programs/moon-buggy/moon-buggy-1.1.0.tar.gz
- **SHA256**: 259ae6e7b1838c40532af5c0f20cd7c6173cd5c552ede408114064475bcfc5b6

## Build System
- **Type**: Autotools (configure + make)
- **configure.ac**: AC_INIT([moon-buggy],[1.1.0],[voss@seehuhn.de]), AM_INIT_AUTOMAKE
- **AC_CANONICAL_HOST**: 使用 host triplet 判断平台特性
- **JV_CHECK_CURSES**: 自定义 m4 宏（acinclude.m4），检测 curses 头文件和库
- **Release tarball**: 已包含预生成的 configure 和 Makefile.in，无需 bootstrap

## Build Configuration
- `--host=aarch64-unknown-linux-ohos` — OHOS 交叉编译
- `--build=aarch64-unknown-linux-gnu` — 显式指定 build triplet，绕过 config.guess 无法识别 HarmonyOS 的问题
- `--with-curses-libs=<ncurses-package>/lib/lib<cpp_info-core-library>.a` — 显式链接 Conan 依赖导出的 ncurses 宽字符静态库，兼容 pthread 构建的 `libncursestw.a`
- `--with-curses-header=<ncurses.h>` — 强制指定 curses 头文件为 ncurses.h（跳过 JV_CHECK_CURSES 检测）
- **Compiler**: clang/clang++ (aarch64)
- **CFLAGS**: `-I<ncurses-package>/include` — 从 Conan 依赖读取 ncurses 头文件路径
- **LDFLAGS**: `-L<ncurses-package>/lib` — 从 Conan 依赖读取 ncurses 静态库路径

## Dependencies
- **ncurses/6.5**: 已适配 OHOS 的独立 Conan 源码依赖，静态宽字符构建
  - include/lib 路径和核心库名通过 `self.dependencies["ncurses"].cpp_info` 获取
  - 不提交或复制任何预编译 ncurses 二进制

## Issues Encountered
1. **OHOS shebang (E165)**: configure 脚本使用 `#! /bin/sh`，OHOS 无 /bin/sh。在 build() 中替换为 `#!/system/bin/sh`。
2. **ncurses 库检测**: JV_CHECK_CURSES 宏默认尝试 AC_CHECK_LIB(curses) 和 AC_CHECK_LIB(ncurses)，但依赖包提供宽字符静态库。使用 Conan `cpp_info.libs` 导出的核心库绝对路径跳过 AC_CHECK_LIB 直接指定；普通 widec 构建为 `libncursesw.a`，pthread + widec 构建为 `libncursestw.a`。
3. **config.guess 不识别 OHOS**: configure 的 config.guess 无法识别 HarmonyOS (UNAME_SYSTEM=HarmonyOS)，使用 `--build=aarch64-unknown-linux-gnu` 显式指定 build triplet 绕过。
4. **config.status 临时目录权限 (E114)**: HMDFS 文件系统上 mktemp -d 创建的临时目录权限为 drwx--S--- (setgid + umask 077)，导致 config.status 无法在其中创建 subs1.awk 文件，报 "Permission denied" / "could not setup config files machinery"。修复：在 build() 中 patch configure 的 `ac_tmp=$tmp` 为固定临时目录路径（`$TMPDIR/moon-buggy-conan-fixed`），该目录预先创建且权限正常。
5. **ncurses dev 文件路径**: 由 Conan 解析 `ncurses/6.5` 源码依赖，并从依赖 `cpp_info` 生成 -I、-L 和系统库标志，避免缓存布局、固定库名和系统路径假设。
6. **curses 头文件检测失败 (CI build #7736)**: JV_CHECK_CURSES 宏 (acinclude.m4) 的 step 2 用 `AC_CHECK_HEADERS(curses.h ncurses.h ncurses/ncurses.h ncurses/curses.h, break)` 检测头文件，该检测依赖 CPPFLAGS。但 Conan AutotoolsToolchain 只把 `-I` 加到 CFLAGS (`extra_cflags`)，不加到 CPPFLAGS，导致 AC_CHECK_HEADERS 检测失败。检测失败后 moon-buggy.h 默认 `#include <curses.h>`，而 OHOS 系统只提供 `ncurses.h`（无 `curses.h`），编译时报 `'curses.h' file not found`。修复：用 `--with-curses-header=<ncurses.h>` 跳过检测，强制指定 `CURSES_HEADER` 为 `<ncurses.h>`（见 acinclude.m4 JV_CHECK_CURSES step 2 的 `AC_ARG_WITH(curses-header)` 逻辑）。
7. **安装阶段 jobserver 和 Texinfo**: Conan 的全局并行度会让 `autotools.install()` 调用 `make install -jN`，但 HMDFS 不支持 jobserver FIFO；`install-data` 还会触发设备上不存在的 makeinfo。修复：OHOS 使用 `autotools.install(target="install-exec", args=["-j1"])`，再手动复制预生成 info 和构建生成的 man 文件。

## Test
- **上游测试**: moon-buggy 源码无 tests/ 目录；无 `make check` 目标
- **Homebrew formula test**: `assert_match(/Moon-Buggy #{version}$/, shell_output("#{bin}/moon-buggy -V"))`
- **test_package**: 改编自 Homebrew formula test，验证 `moon-buggy -V` 输出 `Moon-Buggy 1.1.0`
  - Test 1: `moon-buggy -V` — 验证版本输出匹配 `Moon-Buggy 1.1.0`
  - 交互式游戏模式无法在 CI 环境中测试（需要终端）
- **HarmonyOS 真机结果 (2026-08-07)**: `conan create`、二进制签名和 test_package 全部通过，输出 `PASS: Moon-Buggy 1.1.0`

## Installed Files
- bin/moon-buggy — 游戏主二进制
- share/man/man6/moon-buggy.6 — man page
- share/info/moon-buggy.info — info 文档

## Notes
- moon-buggy 是 CLI 游戏应用程序 (application)，非库。package_info 中 libs=[]，bindirs=["bin"]。
- 游戏使用 ncurses 在终端中渲染画面，需要交互式终端运行。
- Release tarball 包含预生成的 configure、Makefile.in，无需 bootstrap。
- 已在 OHOS 6.0 aarch64 真机上完成源码构建、打包、签名和消费者测试。
