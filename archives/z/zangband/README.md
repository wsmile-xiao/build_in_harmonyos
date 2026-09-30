# Zangband

> 基于 Angband 的经典 roguelike 地牢探险游戏，带荒野/城镇地图与 Lua 脚本扩展。

## 简介

Zangband（ZAngband）是 Angband 的一个著名变体，属于传统 roguelike 类型的地牢探险
游戏。玩家扮演一名冒险者，深入随机生成的多层地牢，与上百种怪物战斗、搜集装备与
神器，最终挑战终极 boss。

相比原版 Angband，Zangband 引入了**荒野（wilderness）与城镇地图**、更多怪物与
物品种类、以及任务系统等扩展内容。游戏自带完整的 ASCII 字符界面，也可选用图形
贴图模式。

游戏的**游戏逻辑大量使用 Lua 脚本**（`lib/script/`），并通过 tolua 在构建期把
`src/l-*.pkg` 接口描述文件生成为 C 绑定代码，因此构建过程包含一个代码生成步骤。

## 功能验证

```bash
zangband -h
# Usage: angband [options] [-- subopts]
#   -n       Start a new character
#   ...
#   -mgcu    To use GCU (GNU Curses)
```

## OHOS 适配要点

- **终端前端使用 ncurses（GNU Curses）端口**。OHOS SDK 的 sysroot 只随附运行期
  stub `libncurses.so.6`（无 `curses.h`、无链接符号），因此必须依赖本仓库适配的
  `ncurses/6.6`（静态宽字符库 `libncursesw.a` + 头文件）。
- **旧式 autoconf 需要注入交叉编译探测结果**。上游使用 2005 年的 autoconf
  （`configure.in`，非 automake），其 `AC_CHECK_SIZEOF`/`AC_FUNC_*` 需要运行探测
  程序；交叉编译下通过 `--cache-file` 提供已知的 aarch64/musl 结果。
- **`tolua` 是构建期主机工具**。它把 `src/l-*.pkg` 生成为 `src/l-*.c`，必须在
  构建机上运行，因此用构建机编译器单独编译；且 `tolua.c` 由 `argv[0]` 推导
  `.lua` 脚本目录，主机版二进制须放在 `src/lua/` 内，否则会静默失败。
- **移除无用的 `-lz` 依赖**。`configure.in` 的 `AC_CHECK_LIB([z],[main])` 会无条件
  链接 zlib，但程序并不使用；移除后二进制只依赖 `libc.so`。
- 关闭 X11 / GTK / Tcl-Tk 前端与 setgid 安装逻辑（`--with-x11=no --with-gtk=no
  --with-tcltk=no --with-setgid=no`）。

### 已知限制

- 交互式字符界面依赖 **terminfo 数据库**。OHOS SDK sysroot、qemu 运行根与
  DAYU200 设备均不提供 terminfo，且设备 `hdc shell` 无 TTY，故 `-mgcu` 交互界面
  无法在自动化环境端到端运行。数据解析与 Lua 脚本引擎路径已由真机消费者用例
  覆盖（`reports/test-report.md`）。
- 上游**未提供测试套件**（`make test` 仅回显变量，`lib/script/test.lua` 为未完成
  的注释）。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| ncurses | 6.6 | 终端界面（静态宽字符库 `libncursesw.a`），仓库内已有适配 |

运行时：仅依赖 `libc.so`（musl）。

## 参考

- [SourceForge 项目页](https://sourceforge.net/projects/zangband/)
- [源码下载](https://downloads.sourceforge.net/zangband/zangband-2.7.5pre1.tar.gz)
- [Angband 官网](https://angband.github.io/angband/)
