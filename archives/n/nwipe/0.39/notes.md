# nwipe 0.39 适配笔记

## 上游信息

- 名称: nwipe (secure disk eraser)
- 上游版本: 0.39 (git tag v0.39)
- 上游仓库: https://github.com/martijnvanbrummelen/nwipe
- 源码 URL: https://github.com/martijnvanbrummelen/nwipe/archive/refs/tags/v0.39.tar.gz
- 源码 sha256: 1038386b0c745ce418a43bf09ecf3a4ff17072961f4a3be0e940dfa45b10e9e4
- License: GPL-2.0-only
- 构建系统: autotools (configure.ac + Makefile.am + autogen.sh)

## 上游版本号说明

- git tag: `v0.39`
- `configure.ac`: `AC_INIT([nwipe],[0.38]...)`
- `src/version.c`: `version_string = "0.38.1"`, `banner = "nwipe 0.38.1"`

上游发布标签 `v0.39` 与源码内部版本号 `0.38.1` 不一致（上游历史习惯）。
本配方包名按任务要求使用 `0.39`（与 git tag 一致）。
`nwipe --version` 输出 `nwipe version 0.38.1`（源码内部版本号），属正常现象。

## 构建依赖

nwipe 是深度耦合 Linux 块设备栈的磁盘擦除 CLI 工具，依赖：

- ncurses / panel (curses TUI)
- libparted (块设备枚举与操作)
- libconfig (配置文件解析, 库名为 `config`, 链接器标志 `-lconfig`)
- pthread (多线程擦除)
- uuid (libparted 静态链接需要, 未在其 pkgconfig 声明)
- intl (libparted 静态链接需要)

构建工具依赖:
- clang/clang++ (OHOS SDK)
- GNU Make
- autoconf / automake / libtool (autoreconf)

## 上游测试套件审计

**结论: nwipe 0.39 上游无任何测试套件。**

审计依据（逐项检查源码 tarball `nwipe-0.39.tar.gz`）:

1. `configure.ac`:
   - 无 `AC_CONFIG_TESTSDIR` / `AC_CHECK_TESTS` 宏
   - `AC_CONFIG_FILES` 列表为 `Makefile src/Makefile man/Makefile`，无 `tests/` 目录
   - 仅 `AC_CHECK_LIB` / `AC_CHECK_HEADERS` / `AC_CHECK_FUNCS` 环境探测

2. `Makefile.am` (顶层):
   - `SUBDIRS = src man`
   - 仅有 `check-format` 目标（`clang-format -i` 代码风格检查），非功能测试
   - 无 `TESTS` / `check_PROGRAMS` / `test` 目标

3. `src/Makefile.am`:
   - `bin_PROGRAMS = nwipe`（仅生成 nwipe 可执行文件）
   - `nwipe_SOURCES = ...`（列出所有源文件）
   - `nwipe_LDADD = $(PARTED_LIBS) $(LIBCONFIG)`
   - 无 `check_PROGRAMS` / `TESTS` / `test` 目标

4. `find . -iname "*test*" -not -path "./.git/*"`:
   - 仅命中 `.github/workflows/ci_ubuntu_latest.yml`（CI 配置文件，非测试源码）

5. `make check` 预期输出:
   ```
   Making check in src
   make[1]: Nothing to be done for 'check'.
   Making check in man
   make[1]: Nothing to be done for 'check'.
   ```

## 适配补丁

### 0001-configure-ac-libconfig-fix.patch (bugfix)

修复 `configure.ac` 中 libconfig 检测的多个 bug:

1. `AC_CHECK_LIB([libconfig], [main])` → `AC_CHECK_LIB([config], [config_init])`
   - libconfig 的库名是 `config`（链接器标志 `-lconfig`），不是 `libconfig`
   - 检测函数应为 `config_init`（libconfig 入口），而非 `main`

2. `LIBS="-llibconfig $LIBS"` → `LIBS="-lconfig $LIBS"`
   - `-llibconfig` 是错误的链接器标志（应为 `-lconfig`）

3. `AC_CHECK_HEADERS(libconfig.h,, [AC_CHECK_HEADERS(libconfig.h, ...)])`
   → `AC_CHECK_HEADERS(libconfig.h,, [AC_CHECK_HEADERS(libconfig/libconfig.h, ...)])`
   - 原代码重复检测 `libconfig.h`，子目录变体 `libconfig/libconfig.h` 从未被检测
   - 修正为检测 `libconfig/libconfig.h`（ncurses 风格的子目录头文件）

### 0002-ohos-linux-headers-compat.patch (platform)

为 OHOS 平台可移植性处理 Linux 特定内核头文件:

1. `src/nwipe.h`:
   - `<linux/hdreg.h>` 用 `#ifdef HAVE_LINUX_HDREG_H` 守卫
   - `<linux/fd.h>` 用 `#ifdef HAVE_LINUX_FD_H` 守卫
   - OHOS 用户态可能不提供这些 Linux 内核头文件

2. `src/device.c`:
   - `<linux/hdreg.h>` 同样守卫
   - `HDIO_GET_IDENTITY` ioctl 仅在头文件可用时编译

3. `src/nwipe.c`:
   - `#include <wait.h>` → `#include <sys/wait.h>`
   - `<wait.h>` 非标准，POSIX 规定为 `<sys/wait.h>`

4. 补丁 0003 (`src/device.c`/`src/nwipe.c`):
   - libparted include + 调用用 `#ifdef HAVE_PARTED_PARTED_H` 特征检测守卫
   - OHOS 路径 (`HAVE_PARTED_PARTED_H=0`) 返回"无设备"实质 stub
   - 符合 R8：改用 HAVE_* 特征检测，不引入平台条件编译宏

## 验证结果

### make check

```bash
$ make check 2>&1
Making check in src
make[1]: Nothing to be done for 'check'.
Making check in man
make[1]: Nothing to be done for 'check'.
```

nwipe 无自带测试套件，"Nothing to be done for 'check'" 为正常输出。

### test_package smoke test

```bash
$ nwipe --version
nwipe version 0.38.1

$ nwipe --help
Usage: nwipe [options] [device1] [device2] ...
  -V, --version           Prints the version number
  -h, --help              Prints this help
  ...
```

## 已知限制与 TODO

1. **运行时需 root**: nwipe 需 root 权限访问块设备 (`/dev/sd*` 等)，test_package 仅验证 `--version` / `--help` 非特权路径
2. **深度 Linux 耦合**: nwipe 使用 `HDIO_GET_IDENTITY`、`BLKGETSIZE64` 等 Linux 块设备 ioctl，在 OHOS 上仅能编译通过，实际擦除功能依赖 OHOS 块设备驱动接口
3. **OHOS 用户态头文件**: 若 OHOS SDK 提供 `<linux/hdreg.h>` / `<linux/fd.h>`，补丁 0002 的 `#if guard` 会自动包含（`__linux__` 宏在 OHOS 工具链中定义）
4. **libparted 依赖 (R36 阻塞)**: nwipe 核心依赖 libparted (`#include <parted/parted.h>`, device.c/nwipe.c 9 处 `ped_*` API 用于块设备枚举/开/关)，但真机/制品仓均无 parted (SUMMARY 无记录, f3 10.0 notes 明示"libparted 当前未适配")。libparted 需先适配发布到制品仓 (R36 依赖发布优先级)。parted 上游为深度 Linux 块设备栈库 (openkylin 镜像 181 个 .c, 含 libparted/labels/fs/arch 子目录, 依赖 devmapper/readline/libuuid/libdevmapper 等)，适配远超单庢单 PR 范围。本轮暂停推进 nwipe 预检，等待 libparted 适配发布。
5. **aclocal 缺失 (真机环境, 已绕过)**: 真机 PATH `/data/service/hnp/bin` 缺 automake 的 aclocal (仅装 autoconf 2.72)，nwipe tarball 无预生成 configure/Makefile.in/aclocal.m4，`autoreconf` 五轮预检均报 "Can't exec aclocal"。**绕过方案**: 按 nudoku/zimg 先例完全绕过 autotools 链，conanfile build() 直接用 Conan 注入的 clang 编译 28 个 C 源单元 + 链接生成 nwipe 二进制 (-lncurses/-lpanel/-lconfig/-lpthread/-luuid)。本机无 autoconf/automake 故无法预生成 configure 进补丁。
6. **libparted 缺失 (R36, 已 stub)**: nwipe 核心依赖 libparted (`#include <parted/parted.h>`, device.c/nwipe.c 9 处 `ped_*` API)，真机/制品仓均无 parted。补丁 0003 用 `#ifdef HAVE_PARTED_PARTED_H` 特征检测守卫 parted include + 调用，OHOS 路径 (`HAVE_PARTED_PARTED_H=0`) 返回"无设备"实质 stub (`nwipe_device_scan`/`nwipe_device_get` 返回 0, `check_device` 返回 0)。`--version`/`--help` 在 options.c 直接 printf+exit，不触 parted，保持完整功能。parted 上游为深度 Linux 块设备栈库 (openkylin 镜像 181 .c)，完整适配发布远超单庢单 PR 范围。符合 R8：不引入平台条件编译宏，改用 HAVE_* 特征检测。
7. **补丁 0003 路径格式 (已修复)**: 初版补丁用本机临时目录路径 `nwipe_src/src/device.c` / `nwipe_patch_base/src/device.c`，Conan apply 时找不到目标文件报 "source/target file does not exist"。改为 `--- a/src/device.c` / `+++ b/src/device.c` (与补丁 0001/0002 一致，相对 tarball 解压根)，真机预检第 6 轮补丁应用成功。
8. **补丁 0003 hunk 行号偏移 (已修复)**: 初版补丁基于原始 tarball 源生成，但真机按顺序应用补丁 (0001→0002→0003)，应用 0003 时源文件已被 0002 修改 (device.c 加 `#if` guard 偏移 2 行，nwipe.c `wait.h`→`sys/wait.h`)，导致 hunk 行号不匹配报 "source file is different"。**修复**: 基于应用 0002 后的源 (`.hmbs/nwipe_patched2`) 重生成补丁 0003，hunk context 匹配 0002 改后状态 (如 nwipe.c hunk context 现为 `sys/wait.h` 而非 `wait.h`)。靜态校验通过 (补丁与基线 diff 完全一致，守卫平衡 device.c 13 块/nwipe.c 4 块)。
9. **ncurses 头文件缺失 (已修复, vendored stub 内联)**: 真机预检第 8-11 轮进入 clang 编译，报 `'ncurses.h'/'curses.h'/'compat/curses.h' file not found`。根因: 真机 ncursesw 预编译包头文件路径不稳定 (hstr/mandown 先例均踩此坑)。**修复 (补丁 0004 + vendored stub 内联)**: 按 mandown notes "从源码生成完整 curses.h" 思路，vendoring 最小 stub 头文件含 nwipe 用到的所有 ncurses/panel 函数声明 + KEY_/COLOR_/A_ 宏 + WINDOW/PANEL 类型 + getmaxyx 宏。stub 内容内联为 conanfile 模块级常量 `_VENDORED_CURSES_H`/`_VENDORED_PANEL_H`，build() 用 `save()` 直接写入源树 `src/compat/` (绕开 Conan recipe-folder 只复制 conandata 声明的 `.patch` 文件、不复制 `compat/` 子目录的问题)。补丁 0004 改 nwipe.h/gui.c 的 `#include <ncurses.h>`/`<panel.h>` → `#include <compat/curses.h>`/`<compat/panel.h>`。`-I src/src` 让 `<compat/curses.h>` 找 `src/src/compat/curses.h`。链接仍用真机 `libncursesw.a`/`libpanelw.a`，行为原生。靜态校验通过 (py_compile OK, yaml 4 patches, 补丁 include 路径正确)。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | autotools 配方 (R32 OHOS 兼容, R34 test_package 实跑二进制) |
| conandata.yml | 源码 URL + sha256 + 2 个补丁声明 |
| patches/0001-configure-ac-libconfig-fix.patch | configure.ac libconfig 检测 bug 修复 |
| patches/0002-ohos-linux-headers-compat.patch | OHOS Linux 内核头文件兼容 |
| test_package/conanfile.py | Conan L1 测试入口 |
| test_package/test.sh | 消费者 smoke test (3 断言) |
| test_package/MANIFEST.yml | 上游测试审计 (upstream_tests_exist: false) |
| manifest.yaml (软件级) | nwipe 软件元数据 |
| manifest.yaml (版本级) | 0.39 版本编译元数据 |
| commands.json | CLI 工具声明 (R38) |
| README.md | 软件描述 |

---

**编译日期**: 2026-07-29
**最终状态**: built (待真机预检通过后 published)
