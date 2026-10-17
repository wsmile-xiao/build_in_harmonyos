# DRAFT-cracklib-2.10.3-dist-missing-check-scripts

> Contributor: 2301_76770579 | Status: Draft | Updated: 2026-09-09
> Source: cracklib 2.10.3 HarmonyOS PC 适配（发布包缺 check 脚本 → 建典+API 等效覆盖）

## 现象

cracklib 2.10.3 官方 release tarball（`releases/download/v2.10.3/cracklib-2.10.3.tar.xz`）
里 `util/Makefile.am` 声明了 `check_SCRIPTS = both-endian.sh checkdict.sh`，
但**这两个脚本根本不在 tarball 里**（上游 `EXTRA_DIST` 遗漏，dist 缺陷）。
同时 3 个 `check_PROGRAMS`（testlib/testnum/teststr）是 **stdin 交互驱动**
（提示 "enter dictionary words..." 逐行读），无脚本驱动就没法自动化。

→ 发布包内 `make check` 的上游自动化判据**整体不可用**。

## 根因

- 上游仓库 git 里有这两个脚本，release 打包时漏了（check_SCRIPTS 不走
  EXTRA_DIST 自动分发，Makefile.am 里也没补）。
- 交互式驱动离开脚本单独跑只能干等 stdin。

## 解决方案

1. **用上游建典工具链自建字典**：`cracklib-format dicts/cracklib-small |
   cracklib-packer testdict`（54763 词）——这正是 check 脚本内部的第一步。
2. **FascistCheck 公开 API 语义断言**（build() 内实跑）：
   典内词（adoration/bawled）→ 必须拒绝且含 "dictionary word"；
   "abc" → "too short"；强密码 "Xk9#mQ2$vL8p" → NULL（通过）。共 4 条。
3. body/MANIFEST 如实写：上游声明 5（3 程序+2 脚本），发布包不可用原因 =
   dist 缺陷 + 交互驱动，等效覆盖 4 条断言。
4. 裁剪：configure `--without-python --disable-nls` + `make SUBDIRS="lib util"`
   （po/doc/python/dicts 不编）。

## 禁止策略

- 不得声称跑了上游 `make check`（发布包脚本缺失，跑了也是 no-op 假绿）。
- 不得拿 `test-data`（10 词）对 cracklib-small 字典做"典内拒绝"断言——
  那些词是全量字典的弱密码表，不在 small 典里。
- 不得从 git 仓补脚本进发布包配方（conandata 锁定的 tarball 内容为准）。

## 适用范围

发布 tarball 与 git 仓内容不一致（dist 缺测试脚本/数据）的 autotools 库：
如实上报缺口 + 用上游工具链+公开 API 等效覆盖判据。
