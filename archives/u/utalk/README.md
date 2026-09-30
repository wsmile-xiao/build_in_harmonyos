# utalk

`utalk` 是一个基于 **UDP**（自研 SRDP 协议）的全屏一对一文本聊天客户端，是 Unix `talk` 的替代实现。相比基于 TCP 的 `talk`，SRDP 在高丢包链路上响应更快；界面支持滚动回看、vi/emacs 键绑定、地址别名等。它与 BSD `talk` **不兼容**，双方都需使用 utalk。

- **上游**: https://utalk.ourproject.org/ （Roger Espel Llima / E. Bosch）
- **版本**: 1.0.2
- **许可证**: GPL-2.0-or-later
- **语言 / 构建系统**: ANSI C / 手写 POSIX Makefile（无 autotools / cmake / meson）
- **产物**: 单一可执行文件 `utalk`（CLI 工具）

## OHOS 适配

- **静态 ncurses（R26）**：`ncurses` 为系统同名库，必须静态链接（`libncursesw.a`），否则运行期会劫持系统 `libncursesw.so`。
- **符号冲突**：静态 `libncursesw.a` 自带 `beep` 符号，与 utalk 的 `termcap.c:beep()` 重名；链接时加 `-Wl,--allow-multiple-definition`（目标文件定义优先）。
- **CFLAGS 不可覆盖**：Makefile 的 `OPTS` 含 `-DLIBDIR="..."`（`menu.c` 的 `HELPFILE` 宏依赖它）；命令行覆盖 `CFLAGS` 会丢失该定义导致编译失败。
- **分阶段安装**：上游 `make install` 会 `strip` 并 `chown root:root`，在无 root 环境下不可用；`package()` 改为普通拷贝。
- **terminfo 内置**：ncurses 全屏需 terminfo 数据库，OHOS 系统 terminfo 极少，故打包 ncurses terminfo 并通过 `TERMINFO` 运行环境变量导出。

## 依赖

- `ncurses/6.6`（宽字符、静态；唯一第三方依赖）

## 上游与源码地址（可达性实测）

| 项 | 值 | 实测 |
|---|---|---|
| 项目官网 | `https://utalk.ourproject.org/` | HTTP **403**（Cloudflare 防护拦截匿名客户端；站点存活，无直链） |
| 历史地址 | `https://www.iagora.com/~espel/utalk/`、`https://www.eleves.ens.fr/home/espel/utalk/` | HTTP **404** |
| 源码地址 | `https://deb.debian.org/debian/pool/main/u/utalk/utalk_1.0.2.orig.tar.gz` | HTTP **200**，sha256 `6158312b…8aa5c` 与 conandata 声明一致 ✅ |

- 上游官网由 Cloudflare 防护（对 `curl` 一律 403，返回 "Just a moment..." 挑战页），无可下载直链；故源码取自 Debian pool 中的 **pristine 上游 orig 包**（`.orig.tar.gz` 即上游原始 tarball，非 Debian 重打包物）。
- 该取源方式为本仓库既定惯例：`archives/**/conandata.yml` 共 **458** 处使用 `https://deb.debian.org/…`，含同日（2026-09-29）合并的 `rt-tests/2.10`、`debootstrap/1.0.144`、`pxlib/0.6.9`。

## 测试

- `test_package/test.sh`：8 项断言（含 4 项 OHOS 特有）——`--help`/无参用法输出、非 tty 拒绝执行、ELF 为 AArch64 且静态 ncurses、pty 下 ncurses 屏幕初始化成功。
- **上游无自动化测试**：官方源码包 36 个文件中不含 `stest.c` / `tests/`；`Makefile:58` 的 `test:` 目标依赖未随包发布的 `stest.c`，`make test` 无法运行（`No rule to make target 'stest.o'`）。
