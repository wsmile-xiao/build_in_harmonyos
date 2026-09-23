# dtach 0.9 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-12
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

1. `init-build dtach 0.9 --url=https://downloads.sourceforge.net/project/dtach/dtach/0.9/dtach-0.9.tar.gz`
2. 用 autoconf 2.72 从 configure.ac 重新生成 configure 脚本（原版为 autoconf 2.69 生成）
3. 移除 configure 脚本中临时目录创建代码的 `umask 077`（E011 修复）
4. 在 Makefile.in 中添加 install 目标，增加 prefix/exec_prefix/bindir/mandir/DESTDIR 变量
5. `bash ./configure --prefix=$DEFAULT_PREFIX` — configure 和 config.status 均通过
6. `make -j1` — 编译成功
7. `make install DESTDIR=$TEST_PREFIX` — staging 安装成功
8. `ohc-run.py package` → 生成 dtach-0.9-ohos-aarch64.tar.gz (89KB)
9. 本地安装 `$DEFAULT_PREFIX/bin/dtach --version` 验证通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: can't create ./confXXXXXX/subs1.awk: Permission denied | HMDFS 文件系统的 UID 映射机制导致 `umask 077` 创建的临时目录无法被当前进程写入（E011）。目录权限变为 drwx--S---（setgid 无 group execute），HMDFS 拒绝写入 | 从 configure 脚本中移除 `umask 077`，将 `(umask 077 && mktemp -d)` 改为 `mktemp -d`，`(umask 077 && mkdir)` 改为 `mkdir` |
| 2 | Makefile 无 install 目标 | dtach 0.9 的 Makefile.in 极其精简，不包含 install 规则，且缺少 prefix/exec_prefix/bindir/mandir 变量 | 在 Makefile.in 中添加 `prefix`、`exec_prefix`、`bindir`、`mandir`、`DESTDIR` 变量，以及完整的 install 目标 |

## 源码修改

- `Makefile.in`: 添加 install 目标（含 DESTDIR 支持），增加 prefix/exec_prefix/bindir/mandir 变量
  - 补丁: 0001-Makefile.in.patch (+12/-0)
- `configure`: 用 autoconf 2.72 从 configure.ac 重新生成，然后移除临时目录创建代码中的 `umask 077`
  - 补丁: 0002-configure.patch (+1753/-1631)

## 依赖版本

- 无外部库依赖
- 构建依赖: autoconf 2.72, clang 15.0.4, make 4.4.1

## 验证结果

```bash
$ dtach --version
dtach - version 0.9, compiled on Jun 12 2026 at 02:42:12.

$ file dtach
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

$ readelf -d dtach | grep NEEDED
  0x0000000000000001 (NEEDED)  Shared library: [libc.so]
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| dtach-0.9-ohos-aarch64.tar.gz | 89KB | 预编译包（含 bin/dtach + share/man/man1/dtach.1） |
| dtach-0.9-ohos-aarch64-debug.tar.gz | 31KB | 预编译debug符号包 |
| 0001-Makefile.in.patch | 1KB | Makefile.in 添加 install target 补丁 |
| 0002-configure.patch | ~188KB | configure 脚本重新生成 + umask 077 移除补丁 |

## 注意事项

- **HMDFS umask 077 限制（E011）**：configure/config.status 创建临时目录时不能使用 `umask 077`，否则 HMDFS 会 Permission denied。修复方式：移除 configure 中 `(umask 077 && mktemp)` 和 `(umask 077 && mkdir)` 的 `umask 077`。此问题影响所有使用 autotools 的软件在 HMDFS 上编译。
- **Makefile 缺少 install 目标**：原版 Makefile.in 无 install 规则，已添加含 DESTDIR 支持的 install target。补丁中同时添加了 prefix/exec_prefix/bindir/mandir 变量，确保 configure 可以正确替换路径。
- **无上游自动化测试**：dtach 无 `make check` 目标，Conan `test_package` 负责消费者侧验证。

## Conan 适配补充

- 当前已补齐 Conan 2 配方、`test_package` 和软件级 `commands.json`
- `test_package` 会验证 `--version`、`--help`，并通过 `-N` 模式启动一次最小脱离会话，确认可执行文件可用
- 上游自动化测试统计保持为 0/0

**编译结束**: 2026-06-12 02:45
**最终状态**: built
---

**编译结束**: 2026-06-12 14:34
**最终状态**: built
