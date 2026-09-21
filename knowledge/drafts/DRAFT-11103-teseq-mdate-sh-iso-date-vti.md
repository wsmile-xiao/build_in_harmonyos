# DRAFT-11103：HarmonyOS `ls` 的 ISO-8601 日期击穿 automake VTI 规则（mdate-sh → version.texi 污染 → makeinfo 缺失）

> Contributor: kasumizawa-miyuu | Status: Draft | Updated: 2026-09-20
> Source: feat/teseq-1.1.1（teseq 1.1.1 适配，任务 #11103）

## 背景

teseq 1.1.1 是 GNU autotools 项目（configure/config.status 由 autoconf 2.69 +
automake 1.13 生成，发行 tarball 自带 doc/version.texi、doc/teseq.info 和 man page）。
在 HarmonyOS PC 上做 Conan 适配时，configure 阶段修复 HMDFS `umask 077`（E129 系）
之后，`make install` 阶段连续出现本文描述的文档再生成失败链。

## 错误现象

```text
./mdate-sh: failed parsing 'ls -L -l -d -n /' output
Updating ./doc/version.texi
...（doc/version.texi 被写入整个环境变量表）
makeinfo: command not found
make: *** [Makefile:867: doc/teseq.info] Error 127
```

要点：`mdate-sh` 解析失败但 **不中断配方**，随后 `doc/version.texi` 被“更新”为
`set` 输出的环境变量表，`doc/teseq.info` 的先决条件因此变新，`make install` 触发
`makeinfo`（OHOS 无 texinfo）→ 安装失败。

## 根因链

1. HarmonyOS 的 toybox `ls -L -l -d -n` 输出 ISO-8601 日期
   （`drwx--x--x 19 0 0 4096 2026-09-14 19:58 /`），**没有 Jan..Dec 月份名**；
2. automake 的 `doc/stamp-vti` 规则执行
   `set \`$(SHELL) mdate-sh $$dir/doc/teseq.texi\``，mdate-sh 按“扫描月份名”
   的算法解析 `ls -L -l -d -n /`，找不到月份 → `error "failed parsing '...' output"`
   （exit 1）；
3. 该规则把命令组 `( ... ) > vti.tmp` 作为整体执行，mdate-sh 的失败**不影响**
   `set` 内置命令——裸 `set`（无参数）打印当前 shell 的全部变量到 stdout，于是
   `vti.tmp` 变成环境变量表，`cmp -s` 判定与 `doc/version.texi` 不同并覆盖之；
4. `doc/version.texi` mtime 变新 → `doc/teseq.info` 判定过期 → 调 `makeinfo`
   （OHOS 无 texinfo）→ `make install` 失败。

触发前提：`configure` 是 `stamp-vti` 规则的先决条件
（`stamp-vti: doc/teseq.texi $(top_srcdir)/configure`），任何改写 `configure`
的补丁（例如 E129 的 umask 补丁）都会刷新其 mtime，从而重跑 VTI 规则。

## 修复（本 PR 采用）

补丁 `patches/0001-Makefile.in.patch`：把 `Makefile.in` 中 `stamp-vti` 规则的
配方改为 no-op（`@:`），保留发行 tarball 自带的 `version.texi`/`info`/man page
原样安装。

```diff
-$(srcdir)/doc/stamp-vti: doc/teseq.texi $(top_srcdir)/configure
-	@test -f doc/$(am__dirstamp) || $(MAKE) $(AM_MAKEFLAGS) doc/$(am__dirstamp)
-	@(dir=.; test -f ./doc/teseq.texi || dir=$(srcdir); \
-	set `$(SHELL) $(srcdir)/mdate-sh $$dir/doc/teseq.texi`; \
-	echo "@set UPDATED $$1 $$2 $$3"; \
-	...
-	@cp $(srcdir)/doc/version.texi $@
+$(srcdir)/doc/stamp-vti: doc/teseq.texi $(top_srcdir)/configure
+	@:
```

该补丁让 `scripts/ohc-run.py clean-verify`（G0 干净构建：解包 + 打补丁 +
configure + make + make install）与 `conan create` 都完整通过，无需配方层
mtime 变通。

## 验证

```sh
python3 scripts/ohc-run.py clean-verify teseq 1.1.1   # ✅ 安装产物正常 (2 bin)
python3 scripts/ohc-run.py conan-verify teseq 1.1.1 --profile ohos-aarch64-device
# G0-G4 PASS；make check 28+28+exercise-seqs+2 libcheck 单测全绿
```

## 关系

- 同源阶段问题：E129/E112/E136（HMDFS `umask 077`，configure/config.status 临时目录）。
- 边界：本条发生在 **make/install 的文档再生成阶段**，错误签名是
  `mdate-sh: failed parsing 'ls ...' output` + `makeinfo: command not found`；
  与 E129 系的 `subs1.awk: Permission denied` 不同，但两者常在同一适配中先后出现。
- 适用：automake 项目带 `info_TEXINFOS`/`doc/stamp-vti` 且 configure 被打补丁
  （mtime 刷新）时；修复亦可推广为“把 VTI 规则配方置为 no-op + 保持发行产物”。
