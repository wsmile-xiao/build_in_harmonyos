# lsmount

`lsmount` 是一个把 `/proc/mounts` 渲染成对齐（可选彩色）网格的小型命令行工具，
用 libconfig 读取配置、用 ncurses 的 terminfo 探测终端颜色能力。

上游主页：<https://www.lsmount.org>（其首页自链的官方仓库为
`git://github.com/Llandon/lsmount.git`），许可证 ISC。

## Versions

| Version | Status |
| --- | --- |
| 0.2.4 | built |

Homepage: https://www.lsmount.org

## 适配要点（跨版本通用）

- 构建系统是**裸 Makefile**：无 configure、无 `PREFIX`/`DESTDIR`/`INSTALL` 把手，
  `install` 目标直写 `/usr/bin`、`/etc`、`/usr/share/man` 且依赖宿主 `a2x` 生成 manpage。
  ⇒ 配方只跑 `make`，staging 由 `package()` 完成，不调用 `make install`。
- `CC` 与 `LDFLAGS` 被 simple `=` 烧死（`/usr/bin/gcc`、`-ltermcap -z now`）
  ⇒ 只能用 make **命令行**赋值覆盖（env 无效），覆盖 `LDFLAGS` 时须把 `-z now` 原样带回。
- `CFLAGS`/`LDLIBS` 用 `+=` ⇒ 通过 **env** 注入可保留上游 flags；用命令行赋值反而会把它们全丢。
- OHOS sysroot 的 `libintl.h` 是空壳（不声明 `gettext`）⇒ 需在编译期停用 NLS。
- 依赖在制品仓均为静态：`libconfig/1.7.3`（`libconfig.a`）、`ncurses/6.5`（只有 `libncursesw.a`）。
