# jhead 3.08 适配笔记

## 编译环境
- 构建系统: makefile（简单 Makefile，无 autotools configure 脚本）
- 编译日期: 2026-06-06
- 编译器: clang 15.0.4 (OpenHarmony SDK)
- 链接器: GNU ld.bfd (binutils 2.45)，绕过有缺陷的 SDK lld
- 状态: built

## 编译步骤

1. `ohc-run.py init-build jhead 3.08 --url=https://github.com/Matthias-Wandel/jhead/archive/refs/tags/3.08.tar.gz`
2. 修改 Makefile 以适配鸿蒙 DESTDIR 模式（R20）：
   - 修改 `PREFIX=$(DESTDIR)/usr/local` → `PREFIX=/usr/local`（分离 DESTDIR 和 PREFIX，运行时通过 make 参数覆盖 PREFIX=$DEFAULT_PREFIX）
   - 添加 `CC=clang` 默认值
   - 添加 `LDFLAGS=-fuse-ld=/data/service/hnp/binutils.org/binutils_2.45/bin/ld.bfd`（绕过有缺陷的 SDK lld）
   - 删除 DPKG_BUILDFLAGS 检查块（不适用于 OHOS）
   - 修改 install 目标：所有目录引用前加 $(DESTDIR)（如 `$(DESTDIR)$(BINDIR)` 替代 `$(BINDIR)`）
3. `make PREFIX=$DEFAULT_PREFIX` — 编译成功
4. `make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX` — 隔离安装（R20 DESTDIR 模式）
5. `sign-elf` 签名 jhead 二进制文件
6. 运行测试套件 `tests/runtests` — PASS（退出码 0）
7. `ohc-run.py verify-build jhead 3.08 --install-prefix=$STAGING_PREFIX` — 全部门禁通过
8. `ohc-run.py package jhead 3.08` — 打包完成 (192KB)
9. `make install PREFIX=$DEFAULT_PREFIX`（不带 DESTDIR）— 部署到 $DEFAULT_PREFIX
10. `sign-elf` 签名部署二进制 + `jhead -V` → "Jhead version: 3.08"

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lld 链接器崩溃（libxml2.so.16 加载失败） | OpenHarmony SDK 的 lld 依赖 libxml2.so.16，该库在当前环境中缺失/损坏 | 使用 GNU ld.bfd：`LDFLAGS=-fuse-ld=/data/service/hnp/binutils.org/binutils_2.45/bin/ld.bfd` |
| 2 | Makefile PREFIX 包含 DESTDIR | 原始 `PREFIX=$(DESTDIR)/usr/local` 将 DESTDIR 嵌入 PREFIX，不符合标准 R20 DESTDIR 模式 | 分离 PREFIX 和 DESTDIR：Makefile 默认 PREFIX=/usr/local，运行时通过 make 参数覆盖 PREFIX=$DEFAULT_PREFIX；install 目标使用 $(DESTDIR)$(BINDIR) |
| 3 | G0 干净构建 make 失败（`unknown output-sync type '2'`） | CFLAGS="-fPIC -O2" 按空格拆分后，`-O2` 被 make 解析为 `--output-sync=2` | 将 CFLAGS 移入 manifest.yaml 的 `required_env` 环境变量，不在 configure_options 中传递多 token 值 |
| 4 | 测试 Permission denied | 未签名的 ELF 二进制在鸿蒙上无法执行 | 在运行测试前先对源码目录中的 jhead 执行 sign-elf |
| 5 | jhead --version 不工作 | jhead 使用 `-V` 参数查看版本，不支持 `--version` | 仅 G2 门禁警告，不影响功能；手动验证使用 -V |

## 源码修改

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|----------|
| makefile | DESTDIR 模式适配（R20）+ 链接器适配 | 编辑：PREFIX、CC、LDFLAGS、install 目标 | 已生成补丁 0001-makefile.patch |

## 依赖版本

- clang 15.0.4 (OpenHarmony SDK llvm)
- GNU ld (binutils 2.45) — /data/service/hnp/binutils.org/binutils_2.45/bin/ld.bfd
- 运行时仅依赖 libc.so（musl libc），无其他运行时依赖

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/jhead -V
Jhead version: 3.08

$ /storage/Users/currentUser/usr/local/bin/jhead -nf normal-digicams/fuji-dx10.jpg
fuji-dx10.jpg --> 0401-130448.jpg

$ /storage/Users/currentUser/usr/local/bin/jhead -nofinfo normal-digicams/olympus.jpg
Camera make  : OLYMPUS OPTICAL CO.,LTD
Camera model : C830L,D340R
Date/Time    : 1999:07:18 20:41:25
Resolution   : 160 x 120

$ file /storage/Users/currentUser/usr/local/bin/jhead
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ readelf -d jhead | grep NEEDED
  0x0000000000000001 (NEEDED)   Shared library: [libc.so]
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| jhead-3.08-ohos-aarch64.tar.gz | 192KB | 预编译包（已签名、已 strip） |
| jhead-3.08-ohos-aarch64-debug.tar.gz | 35KB | Debug 符号包 |
| 0001-makefile.patch | 1 个文件 (+8/-11) | Makefile DESTDIR 适配补丁 |

## 注意事项

- jhead 是简单 C 程序，仅有 Makefile 而无 autotools configure 脚本
- 必须使用 ld.bfd 替代 SDK 的 lld（lld 依赖损坏的 libxml2）
- DESTDIR 模式需要分离 PREFIX 和 DESTDIR（原始 Makefile 将 DESTDIR 嵌入 PREFIX）
- jhead 使用 `-V` 参数查看版本号，而非 `--version`
- 鸿蒙上执行 ELF 二进制前必须先签名（sign-elf）

**编译结束**: 2026-07-15
**最终状态**: built
---

**编译结束**: 2026-07-17 10:55
**最终状态**: built
