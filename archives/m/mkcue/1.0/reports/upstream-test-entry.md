# mkcue 1.0 — 上游测试入口核验（真实命令 / 原始输出 / 退出码）

- 日期：2026-09-29
- 源码：`mkcue_1.orig.tar.gz`（sha256 `2aaf57da4d0f2e24329d5e952e90ec182d4aa82e4b2e025283e42370f9494867`）
- 解包树：`/storage/Users/currentUser/tmp/builds/mkcue-1.work`（由 `ohc-run.py init-build` 下载解包）
- 原始日志：`mkcue-1-wt/.task-logs/03-upstream-test-entry.log`

## 结论

**上游 mkcue 1 没有任何自动化测试入口。** 依据如下（均为真实命令与原始输出）：

| # | 命令 | 原始输出（关键） | 退出码 |
|---|------|------------------|--------|
| 1 | `sha256sum mkcue-1.tar.gz` | `2aaf57da4d0f2e24329d5e952e90ec182d4aa82e4b2e025283e42370f9494867` | 0 |
| 2 | `find $SRC \( -iname '*test*' -o -iname '*check*' -o -type d -name tests \) -not -path '*/.git/*'` | **无任何输出** | 0 |
| 3 | `grep -rn -iE 'test\|check' configure.ac GNUmakefile.in aclibs` | 仅 3 行且**均非测试目标**：`configure.ac:33 dnl Checks for programs.`、`configure.ac:38 AC_CHECK_SIZEOF(long)`、`configure.ac:41 if test -z "${INSTALL_DIR}"; then` | 0 |
| 4 | `grep -nE '^[A-Za-z0-9_.%-]+:' GNUmakefile.in`（构建目标清单） | `all:` `mkcue:` `clean:` `maintainer-clean:` `install:` `dist:`；`.PHONY: all clean dist install maintainer-clean` —— **无 `check` / `test` 目标** | 0 |
| 5 | 上游 tarball 文件清单（`tar tzf`） | `AUTHORS COPYING GNUmakefile.in README aclibs aclocal.m4 build/{config.guess,config.sub,install-sh,setup} config.h.in configure configure.ac diskid.cc diskid.h errors.h mkcue.cc osdep/*` —— **无 `tests/`、无 `t/`、无 `*.test`** | 0 |
| 6 | `ls build/` | `config.guess config.sub install-sh setup` —— autotools 辅助脚本，非测试 | 0 |

## 发行版侧复核

Debian 打包（`debian/control`，仅打包元数据，不含上游测试）：

```
Build-Depends: debhelper, debhelper-compat (=13), docbook-to-man
Package: mkcue
Depends: ${shlibs:Depends}, ${misc:Depends}
```

`debian/rules` 只做 `dh` 标准流程（`docbook-to-man debian/mkcue.sgml > mkcue.1` 生成 man page），
**没有 `dh_auto_test`/`TEST_TARGET`/`override_dh_auto_test`**。

## 上游"样例"如何执行（见 `upstream-test-cases.md`）

上游唯一可执行的"样例"是 `README:7-10` 记录的命令行用法。本适配按该用法构造并**实际执行**了
6 条行为用例（`README` 默认设备 / 显式设备 / `-t track-count` 边界 / 非法选项），
全部通过，详见 `upstream-test-cases.md`。

**TOC 读取的 happy path 不可测**：需要真实光学设备（`/dev/cdrom` 与 `CDROMREADTOCHDR` 等
ioctl）。本环境无光驱，`mkcue` 对 `/dev/cdrom` 与任意不存在设备的响应均被实测记录为
`Cannot open '<dev>'` + exit 2，未做任何"跳过即通过"处理。

> `test_package/` 的 9 例**不能替代上游测试统计**：上游测试 = 0（无入口），
> 上游行为用例 = 6（实测），两者在 `test-report.md` 中分列。
