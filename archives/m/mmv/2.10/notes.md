# Adaptation Notes — mmv 2.10 (upstream v2.10)

## Software
- **Name**: mmv
- **Version**: 2.10 (upstream v2.10)
- **Description**: Move, copy, append, and link multiple files with wildcard patterns
- **License**: GPL-3.0-or-later
- **Source**: https://github.com/rrthomas/mmv/releases/download/v2.10/mmv-2.10.tar.gz
- **SHA256**: 2bbba14c099b512b4a7e9effacec53caa06998069d108a5669ff424ffc879d03

## Build System
- **Type**: Autotools (configure + make)
- **configure.ac**: AC_INIT([mmv],[2.10]), AM_INIT_AUTOMAKE
- **Gnulib**: 使用 gnulib 库 (lib/libgnu.a)，release tarball 已包含预生成的 configure 和 cmdline.c/cmdline.h
- **gengetopt**: Makefile.am 中有 `gengetopt < opts.ggo --unamed-opts` 生成 cmdline.h/cmdline.c，release tarball 应已预生成

## Build Configuration
- `--build=aarch64-unknown-linux-gnu` — 参照 bash 库做法，config.sub 可接受此 triplet；不传 --host（默认 host==build），native 编译模式使 make check 可运行
- `--disable-gcc-warnings` — 禁用 GCC 开发者警告，避免严格警告导致构建失败
- **Compiler**: clang/clang++ (aarch64)
- **CFLAGS**: Homebrew formula 在 clang >= 1403 时添加 `-Wno-implicit-function-declaration`

## Dependencies
- **bdw-gc**: Homebrew formula 声明为运行时依赖，但源码分析发现 mmv 2.10 实际未使用：
  - configure.ac 未 PKG_CHECK_MODULES for gc
  - Makefile.am LDADD 仅引用 `$(top_builddir)/lib/libgnu.a`
  - mmv.c 未 `#include <gc/gc.h>` 或类似头文件
  - 结论：mmv 2.10 实际不使用 bdw-gc，Homebrew formula 依赖可能为历史遗留
  - 处理：不声明 bdw-gc 依赖（CI 验证确认 ohpcd remote 中无 bdw-gc/8.2.6，且源码未引用）
- **help2man**: 构建依赖（用于生成 man page），OHOS 环境可能缺失，但 `make install` 时 man page 生成失败不影响二进制安装
- **pkgconf**: 构建依赖（Homebrew formula 声明）
- **gengetopt**: 生成 cmdline.c/cmdline.h（release tarball 已预生成）

## Issues Encountered
1. **OHOS shebang (E165)**: configure 脚本使用 `#! /bin/sh`，OHOS 无 /bin/sh。在 build() 中替换为 `#!/system/bin/sh`。
2. **OHOS umask (E110)**: configure 中 `umask 077` 在 HMDFS 上导致临时目录权限问题。替换为 `umask 002`。
3. **bdw-gc 依赖验证**: 源码分析显示 mmv 2.10 不直接使用 bdw-gc，CI 验证确认 ohpcd remote 中无 bdw-gc/8.2.6 包。已移除该依赖声明。
4. **config.guess/config.sub 不认识 HarmonyOS (E007)**: mmv 2.10 自带的 config.guess (2024-01-01) 无法识别 `uname -s = HarmonyOS`，config.sub 不接受 `aarch64-unknown-linux-ohos` 中的 `ohos` OS（kernel-OS 校验报 "Kernel 'linux' not known to work with OS 'ohos'"）。解决方案：参照 bash 库做法，仅指定 `--build=aarch64-unknown-linux-gnu`（config.sub 可接受），不传 `--host`（默认 host==build，native 编译模式）。同时在 build() 中手动 patch config.guess/config.sub 添加 HarmonyOS 识别（以防 configure 内部调用），不依赖系统 automake 路径。

## Test
- **上游测试**: mmv 源码无 tests/ 目录；`make check` 仅运行 gnulib 模块测试 (lib/)。build() 末尾调用 `autotools.make(target="check")` 运行上游测试，满足 CI L1c 门禁要求。
- **test_package**: 改编自 Homebrew formula test，验证 mmv 的移动/覆盖/符号链接功能
  - Test 1: `mmv -p a b` — 预览模式，应拒绝覆盖已有文件 (exit 1)
  - Test 2: `mmv -d -v a b` — 删除+移动，应将 a 移到 b 并覆盖
  - Test 3: `mmv -s -v b c` — 符号链接，应创建 c 指向 b

## Installed Files
- bin/mmv — 主二进制
- bin/mcp, bin/mln, bin/mad — 通过 install-exec-hook 创建的符号链接（指向 mmv）
- share/man/man1/mmv.1 — man page

## Notes
- mmv 是 CLI 应用程序 (application)，非库。package_info 中 libs=[]，bindirs=["bin"]。
- 安装时 Makefile.am 的 install-exec-hook 会在 bindir 创建 mcp/mln/mad 符号链接。
- Release tarball 包含预生成的 configure、Makefile.in、cmdline.c/cmdline.h，无需 bootstrap。
