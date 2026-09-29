# mkcue 1 适配笔记

## 编译环境
- 构建系统: autotools（随包分发预生成 `configure` + 手写 `GNUmakefile.in`；仅需 GNU make）
- 编译日期: 2026-09-29
- 编译器: clang / clang++ 15.0.4（OHOS SDK；`/data/service/hnp/bin/clang`，target `aarch64-unknown-linux-ohos`）
- 目标: `os=OHOS`、`arch=armv8`、`aarch64-unknown-linux-ohos`、`compiler=clang`、`libcxx=libc++`
- 状态: published
- 依赖: **0 个第三方依赖**（链接行 `mkcue.o mb.o`，无 `-l`）

## 编译步骤

```sh
# 1. 源码（canonical 版本 1）
curl -LO https://ftp.debian.org/debian/pool/main/m/mkcue/mkcue_1.orig.tar.gz
sha256sum mkcue_1.orig.tar.gz
# 2aaf57da4d0f2e24329d5e952e90ec182d4aa82e4b2e025283e42370f9494867

# 2. 补丁（5 枚，见 patches/）
# 3. 交叉编译（Conan 驱动；探索期手工等价命令如下）
./configure --prefix=$DEFAULT_PREFIX --host=aarch64-linux-ohos
make
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./build/config.guess` → `unable to guess system type` | 2002 版 config.guess 无 HarmonyOS 分支；`uname -s` = `HarmonyOS` 不匹配任何已知系统 | `0002-build-config.guess.patch`：在 `*:NetBSD:*:*` 前插入 `*:HarmonyOS:*:*` 分支，输出 `aarch64-unknown-linux-ohos`（E007） |
| 2 | `./build/config.sub aarch64-linux-ohos` → `machine 'aarch64-unknown-linux' not recognized` | 2002 版 config.sub 既不认 `aarch64`/`arm64`，也不认 `linux-ohos` KERNEL-OS 组合 | `0003-build-config.sub.patch`：CPU 列表加 `aarch64 \| arm64`；`maybe_os` 列表加 `linux-ohos*`；在 `-linux*)` 前加 `-linux-ohos*)` 保持原样不再改写为 linux-gnu（E007/E072） |
| 3 | `config.status: can't create ./confstatoCFpmc/subs.sed: Permission denied` → `config.h` 未生成 | HMDFS 将新建目录属主 UID 映射为 20001006，与进程 UID 不同，`umask 077` 的 0700 目录对当前进程不可写 | `0004-configure.patch`：`configure` 中两处 `umask 077` → `umask 022`（E011/E110/E052） |
| 4 | Conan 构建（out-of-tree/VPATH）下 `fatal error: 'diskid.h' file not found` / `'mb.h' file not found` | 手写 `GNUmakefile.in` 非 VPATH-clean：`AC_LINK_FILES` 把 `mb.cc`/`mb.h` 生成在 **build** 目录，`diskid.h`/`types.h` 在 **source** 目录，两个翻译单元双向互相包含 | 不改上游 Makefile，配方 `generate()` 里给 `AutotoolsToolchain` 追加 `-I<source_folder> -I<build_folder>`（R33：flag 来自 toolchain） |
| 5 | `diskid.h:64: error: reference to 'byte' is ambiguous`（C++17） | `diskid.h:31` 有 `using namespace std;`，libc++ `<cstddef>` 引入 `std::byte`；全局 `typedef unsigned char byte;` 与之冲突（探测期手工构建未传 `-std`，clang 15 默认 gnu++14 不触发） | `0005-diskid.h.patch`：本地 typedef 与其两处使用重命名为 `byte_t`（字段名/语义不变，3 行） |
| 6 | `make install DESTDIR=…` → `install: <dst>/bin/mkcue: No such file or directory` | 上游 `GNUmakefile.in` 的 install 规则依赖目标目录已存在：`configure.ac` 已 `AC_SUBST(INSTALL_DIR)`（`install -m 755 -d`），但 Makefile 从未使用该变量 | `0001-GNUmakefile.in.patch`：在该规则里补 `${INSTALL_DIR} ${DESTDIR}${bindir}`（1 行；同时修好 conan `package()` 与 clean-verify 两条路径） |

> 首次用 `patch-autotools-ohos.pl` 处理 config.guess 时，脚本插入的分支只写 `GUESS=...` 而没有
> `echo`/`exit 0`（新版 config.guess 末尾统一 `echo "$GUESS"`，2002 版没有），脚本会继续走到末尾
> 报 "unable to guess"。本配方补上 `echo ${MACHINE}-unknown-linux-ohos; exit 0`。
> 细节见 `reports/framework-findings.md`。

## 源码修改（补丁）

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001-GNUmakefile.in.patch | `GNUmakefile.in` | +1 行：install 规则补 `${INSTALL_DIR} ${DESTDIR}${bindir}` |
| 0002-build-config.guess.patch | `build/config.guess` | +12 行：HarmonyOS 识别分支 |
| 0003-build-config.sub.patch | `build/config.sub` | +4/-1 行：aarch64/arm64 别名 + linux-ohos 组合 |
| 0004-configure.patch | `configure` | +2/-2 行：`umask 077` → `umask 022` |
| 0005-diskid.h.patch | `diskid.h` | +3/-3 行：`byte` → `byte_t`（避开 C++17 `std::byte`） |

**源码`.cc/.cpp` 业务逻辑零改动**：`mkcue.cc` / `osdep/mb_linux.cpp` / `osdep/mb_linux.h` 未做任何修改；
`<linux/cdrom.h>` 与 `CDROM*` ioctl 由 OHOS SDK sysroot 提供。

## 依赖版本

| 依赖 | 版本 | 类型 | 实测 |
|------|------|------|------|
| （无第三方依赖） | — | — | `conan download` 探测 0/0 |
| GNU make | 4.4.1（基环境自带） | 构建工具链基础件 | 本地 `make --version` → GNU Make 4.4.1 |
| clang / clang++ | 15.0.4（OHOS SDK） | 编译器基础件 | `/data/service/hnp/bin/clang --version` |

## 验证结果

```sh
# 探索期手工交叉编译（真实命令与退出码见 .task-logs/）
$ ./configure --prefix=/storage/Users/currentUser/usr/local --host=aarch64-linux-ohos   # exit 0
$ make                                                                                    # exit 0
$ file mkcue
mkcue: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
$ llvm-readelf -S mkcue | grep codesign
  [37] .codesign   PROGBITS  ...
$ mkcue -t 0            # → "invalid track-count 0", exit 2
$ mkcue /nonexistent    # → "Cannot open '/nonexistent-device'", exit 2

# 消费者测试（test_package）
TOTAL=9 PASS=9 FAIL=0 SKIP=0
```

## 注意事项

- 上游**没有自动化测试**（无 `tests/`、`GNUmakefile.in` 无 `check`/`test` 目标）；
  TOC 读取的 happy path 需要真实 CD 硬件，本环境不可达，已在报告中如实标注为不可测，
  未用 test_package 冒充上游测试统计。
- 许可证以 `COPYING` 为准（LGPL-2.1）；`README` 的 "GNU GPL" 为作者的笼统描述。
- 上游为 SVN、无 git commit；版本 1 的源码以 Debian `mkcue_1.orig.tar.gz` 的 sha256 锚定。
---

**编译结束**: 2026-09-29 08:50
**最终状态**: published
