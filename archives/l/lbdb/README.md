# lbdb

> Little Brother's DataBase：面向 MUA（mutt / notmuch / Wanderlust / Gnus …）的轻量邮件别名与
> 地址簿查询工具，用一个 `lbdbq` 前端把多个后端查询模块聚合成统一入口。

## 简介

- 上游：Roland Rosenfeld，<https://www.spinnaker.de/lbdb/>；本包版本 **0.57**，GPL-2.0-or-later。
- 构建系统：autotools（`configure` + 生成的顶层 `Makefile`，autoconf 2.72）。
- 取源官方址：`https://www.spinnaker.de/lbdb/download/lbdb-0.57.tar.gz`
  （sha256 `212fe2e40df5ed3e5496bc5e821e4b0683a6c9523b8885e7e87b634bcf923a88`；
  B 机 3 次独立 GET 均为 208683 B 且逐字节相同，同页有 `.asc` 分离签名）。
- 交付形态：**shell 脚本为主 + perl/awk 辅助 + 3 个小型 C helper**。
  bin 5 枚（`lbdbq`、`lbdb-fetchaddr`、`lbdb_dotlock`、`nodelist2lbdb`、`mutt_ldap_query`）
  + libexec 18 枚（`munge`、`lbdb-munge`、`lbdb_lib`、`palm_lsaddr`、`vcquery`、`fetchaddr`、
  `qpto8bit` 与 `m_bbdb`、`m_fido`、`m_gnomecard`、`m_inmail`、`m_ldap`、`m_muttalias`、`m_palm`、
  `m_passwd`、`m_pine`、`m_vcf`、`m_wanderlust` 共 11 个查询模块）。
  用户入口只有 `lbdbq`，它按配置里的 `LBDB_MODULE_LIST` 调度 libexec 下的模块。

## OHOS 适配要点

- **config.guess 不认 HarmonyOS（E007）**：`patches/0001` 把 config.guess/config.sub 重锚为
  `aarch64-unknown-linux-ohos`；**不使用 `--build/--host`** 绕过（那会让 autoconf 误判交叉编译、
  跳过 `AC_RUN_IFELSE`/`AC_PATH_PROG`，生成错误的 `config.h`）。
- **解释器归一（E049）**：本平台无 `/bin/bash`、无 `/usr/bin/perl`（perl 只在
  `/data/service/hnp/bin/perl`），而 autoconf 模板会把构建机路径烧进 `#!` 行。配方在 configure
  钉 `SH=/bin/sh AWK=/bin/awk`，并在 `package()` 里按 basename 归一：shell → `#! /bin/sh`
  （toybox ash 实测支持本包用到的 `[[ ]]`、数组、`${v//}`、`==`、`local`），
  perl → `#! /usr/bin/env perl`，awk → `#! /bin/awk -f`。实测 20 个已装脚本 0 个机器绑定 shebang。
- **HMDFS / 内核差异**：autoconf `config.status` 的 `mktemp -d` scratch 目录内写文件被拒
  （E129），配方改为 plain `mkdir`；`/tmp` 只读（E002）⇒ 运行期需可写的 `TMPDIR`；
  HMDFS 忽略 chmod ⇒ 嵌套 `mkdir -p` 造的中间目录缺属主 +x，用 `lbdb-fetchaddr -f <已存在目录>/db` 规避。
- **无外部库依赖**：`checking for iconv... yes`（OHOS libc 自带 iconv），`requires` 为空；
  finger/gpg/getent/abook/mutt 等只是运行期可选模块的探测项，缺失即优雅禁用对应 `m_*`。
- **CI smoke 的分栏说明（结果为 `pass`）**：CI 的 L2 只按 `--version/--help` 探测 bin 命令，本包 5 枚 bin 中只有
  `lbdbq --version` 返回 0 ⇒ 4 枚出 `[warn]`（非阻塞），末行 **`L2_RESULT=pass`**（`reports/w3-local-ci.log:459`）。
  这不是解释器缺失：A3/A4/A5/A6 已分别证明 sh 与 perl 交付脚本在本平台可解析。

## 功能验证

```bash
# 版本横幅（toybox /bin/sh 下可跑）
lbdbq --version            # lbdbq version 0.57

# 采集一封邮件的地址到指定库（避开只读 /tmp 与 HMDFS 嵌套 mkdir）
printf 'From: Joe Bloggs <joe@example.com>\nSubject: hi\n\nhello\n' \
    | lbdb-fetchaddr -a -f "$PWD/m_inmail.db"

# 反向查询该库（m_inmail 模块读 INMAIL_DB）
INMAIL_DB="$PWD/m_inmail.db" lbdbq joe
#   lbdbq: 1 matches  joe@example.com  Joe Bloggs  <date>

# 破坏性对照：查无此人时非零退出并打印 no matches
lbdbq zzzNoSuchPersonZzz ; echo "rc=$?"
```

## 测试口径

- 上游：`tests/` 内 7 个 `.at` 文件 = 6 个用例文件（`m_abook` 1、`m_inmail` 8、`m_mu` 4、
  `m_muttalias` 1、`m_notmuch_addrlookup` 1、`m_vcf` 5）共 **20 个 `AT_SETUP` 用例** + `testsuite.at`
  包装器。声明见 `tests/Makefile.in:21-22`（`TESTSUITE_AT`）与 `:38`（`check-local`），
  `tests/Makefile` 由 `configure.ac:245` 的 `AC_CONFIG_FILES` 生成。20 例已于 2026-09-27 在
  本机 conan 构建目录**全部实跑**（`make -C tests check-local`）：执行 14、通过 12、跳过 6
  （缺 abook / mu / notmuch）、失败 2（`lbdb-fetchmail` / `m_inmail`——HMDFS 不支持 link(2)，
  `lbdb_dotlock` 建不出 `<db>.lock`、`lbdb-fetchaddr` 收尾解锁 ENOENT 返 1）。证据见
  `0.57/reports/` 三日志：`upstream-make-check.log:50`「14 tests were run / 2 failed
  unexpectedly / 6 skipped」、`upstream-testsuite.log`（ok 12 / FAILED 2 / skipped 6）、
  `upstream-skips-only.log` 末行「6 tests were skipped.」。20 例未接入 build() 红门
  （`upstream_test_in_build: false`，待 dotlock 无硬链接回退的用户裁决）。
- 交付：消费者自测 `test_package/test_lbdb.sh`，静态断言站点 **10**（A1–A10），
  verify 与 W3 两次运行均为 `SUMMARY lbdb consumer: total=10 passed=10 failed=0`。

## 参考

- [上游主页](https://www.spinnaker.de/lbdb/)
- [上游下载页（含 .asc 分离签名）](https://www.spinnaker.de/lbdb/download/)
- 逐条收口读数与门禁子行原文见 `0.57/notes.md` §11。
