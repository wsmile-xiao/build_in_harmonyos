# rs

rs 是一个把 **stdin 读入的字段流按列/行重新排布**（可选转置）后写到 stdout 的纯文
本矩阵工具，出自 MirBSD/OpenBSD 血统（源码里带 `$MirOS:` 与 `$OpenBSD:` 标识），
作者为 John Kunze（UCB）与 Thorsten Glaser（mirabilos）。典型用法是把一长列字段
压成多列，或在列数固定的表格里做行列转置：

```sh
seq 9 | rs 3 3          # 排成 3 行 3 列
pr -o3 -s' ' file | rs  # 规整成表格
rs -e 0 5               # 每行一个条目，转置排布
```

## 功能概述

- 读 stdin、写 stdout，不做任何 I/O 之外的副作用（无网络、无特权设备、无配置文件）
- 按列宽（显示宽度）对齐，支持制表符/自定义分隔符（`-c` / `-d`）
- 转置与"每行一条目"两种排布语义（默认 vs `-e`）
- 支持 UTF-8 显示宽度计算（依赖 `LC_ALL` 指向 UTF-8 locale）
- 行数/列数参数走 OpenBSD `strtonum(3)`，能区分 `invalid` / `too small` / `too large`

## OHOS 适配

本包是"上游源码零修改"的适配（`patches_applied: []`）：

| 适配点 | 做法 |
|---|---|
| 上游 Makefile 是 BSD make（`.include <bsd.prog.mk>`），GNU make 下 `Makefile:13: *** missing separator` | 配方逐编译单元直接驱动 clang，编译 `rs.c` `utf8.c` `.linked/strtonum.c`（+ 一个兼容 TU）后链接；上游 Makefile 一字节不改 |
| OpenBSD 专有 `strtonum(3)`（`rs.c` 六处调用） | 用**上游自带**的 `.linked/strtonum.c`，并打开上游自己在 `rs.h` 里预留的两个移植开关 `NEED_STRTONUM`、`MBSDPORT_H` |
| OHOS musl 的 `sys/cdefs.h` 不定义 `__RCSID` | 经上游预留的 `MBSDPORT_H` 钩子把 `rs.h`（内含 MirBSD `<sys/cdefs.h>` 后备）引到 `.linked/strtonum.c` 里 |
| OpenBSD `reallocarray(3)`：OHOS 运行期 musl 有、SDK 链接桩 `libc.so` 无 | 补独立兼容 TU `compat_reallocarray.c`（**返回值与 OpenBSD reallocarray(3) 手册页一致：溢出返回 NULL；errno 取值不承诺**——本平台 B 机实测：本实现溢出置 errno=34 即 ERANGE，OHOS musl 运行期置 errno=12 即 ENOMEM（手册页口径）；两常量实测 ERANGE=34、ENOMEM=12（python3 errno 与 clang 编译探针两口径一致），与 compat_reallocarray.c 文件头、`notes.md` §7.1 同源）；不用"混链静态 libc"，实测那样会让产物一跑就 SIGSEGV |
| 回归语料 `check.t` 在包内、驱动 `check.pl` 在 mksh 源码树里 | 随配方提供等价 runner `check_t_runner.py`，在 `build()` 里真实执行全部 13 条用例 |

已知限制（不是适配缺陷）：

- 上游语料里的 `unicode-3-optu8` 用例被上游自己标注 `category: os:mirbsd`——
  该期望只在 MirBSD 的 OptU8 字符集层下成立。本平台仍会真实执行它并记录差异
  （musl 把非法 UTF-8 序列渲染成 `?`），记为 SKIP 而非 FAIL；其镜像用例
  `unicode-3-utf8`（`category: !os:mirbsd`，即"本平台该这样"）PASS。
- 上游无 `--version` / `-V`（`getopt` 串里就没有），版本信息只能从 man 页取。

## 依赖关系

- **编译依赖**：clang（OHOS SDK 自带）、Conan 2.x；无第三方库
- **运行依赖**：仅 libc。UTF-8 宽度用例需要 `LC_ALL` 指向 UTF-8 locale（如 `C.UTF-8`）

## 参考资料

- 上游发布目录（Debian `watch` 所指）：<https://www.mirbsd.org/MirOS/dist/mir/rs/>
- **本包现行取源（2026-09-28 收尾-8 换源）**：`https://deb.debian.org/debian/pool/main/r/rs/rs_20200313.orig.tar.gz`
  （pristine `.orig`，与上游官方件 `curl -L` 实测同为 12571B、sha256 同串、`cmp` 逐字节相同；
  sha256 `919215dc9fe85a27a30bf63d56406cfb503f9fc9820323c4bd3bfe75a6a3bc3f` 一字未动）。
  **为什么不用上游官方直链**：作者自家 Evolvis 服 `https://mbsd.evolvis.org/MirOS/dist/mir/rs/rs-20200313.tar.gz`
  在 CI worker 侧两轮实测 `[Errno 111] Connection refused`（build#63232/CI-022、build#63490/CI-007），
  而 A/B 机 `curl -L` 均 200 ⇒ 定性为该主机拒连本 worker，非源码站全挂；同一棵 dist 树的路径与目录页
  仍见 <https://mbsd.evolvis.org/MirOS/dist/mir/rs/>（端点实测与两树对账见 `20200313/notes.md` §0/§7.10/§7.11；
  `www.mirbsd.org` 一侧 DNS 可解但 TCP 80/443 在本工作区不可达）。PF7 口径按 R52 记 P1-已例外处置。
- 上游 CVS 浏览（Debian `upstream/metadata` 所指）：<https://www.mirbsd.org/cvs.cgi/src/usr.bin/rs/>
- 本包取源（现行＝pristine `.orig`；09-27 的官方直链闭环与 09-28 的 worker 拒连换源）、
  pristine tarball 与摘要核验、R39/PF7 处置（现行 P1-已例外处置）取证：见 `20200313/notes.md` §7.10/§7.11
- 许可证为三合一（BSD-3-Clause / ISC / MirBSD 家族，第三项 SPDX 标识符取 `MirOS`），逐文件归属见 `notes.md` 的「许可证」一节；
  配方 `license` 与软件级 `manifest.yaml` 据 Debian `copyright` 的
  three-fold 声明为 `BSD-3-Clause` + `ISC` + `MirOS` 三项——追加 ISC 的直接理由是**配方侧
  唯一的派生件** `compat_reallocarray.c`（移植自 OpenBSD `reallocarray.c` v1.3，见
  `20200313/manifest.yaml` 的 `shipped_sources_provenance`）；上游侧 ISC 对应自带的
  `utf8.c` 与 `.linked/strtonum.c`；第三项 `MirOS`（SPDX 标识符，Debian `copyright`
  第 67 行的用词是 MirBSD）覆盖 `rs.h` 与打包，`rs.h` 经 `rs.c:52` include 编译进二进制；
  主许可 BSD-3-Clause 一字未改
