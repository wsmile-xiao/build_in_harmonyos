# tmate 2.4.0 适配记录

## 来源

- 上游: https://github.com/tmate-io/tmate , tag `2.4.0`(commit `5e00bfa5e137e76c81888727712ced2b3fd99f5b`)
- 源码归档: `https://github.com/tmate-io/tmate/archive/refs/tags/2.4.0.tar.gz`
- SHA-256: `62b61eb12ab394012c861f6b48ba0bc04ac8765abca13bdde5a4d9105cb16138`(与任务头、首轮依赖分析一致)
- 构建系统: Autotools(autogen.sh → configure → make);上游无自动化测试套件(0/0 N/A,仅 `./tmate -V` 冒烟)

## 依赖(全部 ohpcd 已发布可消费)

| 依赖 | 版本 | 类型 | 说明 |
|---|---|---|---|
| libevent | 2.1.13 | 强制 pkg-config `libevent` | configure.ac PKG_CHECK_MODULES |
| ncurses | 6.6 | 强制 pkg-config `ncursesw` | 0001 探测名对齐(ncurses->ncursesw) |
| msgpack-c | 7.0.0 | 强制 pkg-config `msgpack-c` | 0001 探测名对齐(msgpack->msgpack-c, 满足 >=1.1.0) |
| libssh | 0.11.4 | 强制 pkg-config `libssh` | 满足 >=0.8.4;传递 openssl/1.1.1w + zlib/1.3.1 |
| libutempter | (未发布) | 可选 HAVE_UTEMPTER | 保持禁用,不阻塞 |

## Patch 清单(0001-0010)

- 0001: configure.ac 依赖探测名对齐 msgpack-c/ncursesw
- 0002-0007: 预生成 etc/{compile,config.guess,config.sub,depcomp,install-sh,missing}
- 0008-0010: 预生成 aclocal.m4 / Makefile.in / configure
- 0003 config.guess 含 HarmonyOS 探测块(aarch64/arm/amd64/x86 -> *-unknown-linux-ohos)

## OHOS 构建要点

- TMPDIR=$HOME/tmp;CONFIG_SHELL=/data/service/hnp/bin/bash
- 静态链接(R26);`--prefix=/` + DESTDIR staging 安装
- /tmp 只读场景使用 $HOME/tmp;HMDFS 软链接 rm -f && ln -s

## 状态

- 2026-08-15: 首轮 evidence 依赖分析完成;本轮(round 3) adapt rebuild_required 本地闭环进行中
