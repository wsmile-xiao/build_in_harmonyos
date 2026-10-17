# pd-iemlib — Pure Data 外部对象集合（iemlib）

`iemlib` 是奥地利 IEM / KUG Graz 的 Thomas Musil 为 Pure Data（Pd）写的外部
对象集合：单位与数值换算（`db2v`/`v2db`/`wrap`/`f2note`/`unsymbol`）、递归滤波
（`prvu~`/`rvu~`/`pvu~`/`vcf_filter~`）、t3 系列（`t3_bpe`/`t3_delay`/
`t3_line~`/`t3_metro`/`t3_timer`），以及 **165 个 abstraction** 和 **77 个帮助
补丁**。作者标注它针对 Pd 0.49 编写。

## 用法

iemlib 用上游的 `make-lib-executable=yes` 编译，**整个集合只有一个**
`iemlib.pd_linux`（多对象库），不像 maxlib 那样每个类一个文件。因此 Pd 侧的
用法是「先声明库、再用类」：

```sh
pd -path <pkg>/lib/pd-externals -lib iemlib
```

或在补丁里放一个 `[iemlib]` 空对象（也可以 `[declare -lib iemlib]`），
Pd 会在首次遇到 `[db2v]` 之类的名字前把库装载进来。

## OHOS 适配要点

- 上游用自带 `pd-lib-builder` 构建，`make-lib-executable=yes` → 产出单个
  `iemlib.pd_linux`；该文件导出 `iemlib_setup` 入口点（`nm -D` 可见）。
- `puredata/0.54.1`（application）**不装** Pd API 头：配方在 `source()` 额外
  拉取 `pure-data 0.54-1` 源码树，`PDINCLUDEDIR` 指向其 `src`。iemlib 的
  Makefile 传 `-DHAVE_G_CANVAS_H=1`，`g_canvas.h` 就在同一个 `src/` 目录里。
- `pd-lib-builder` 依据 `$(CC) -dumpmachine` 选中 Linux 分支与 `pd_linux`
  扩展名；`CC` 由 `compiler_executables` 显式传入。
- **无需源码补丁**：全树只用公开的 `m_pd.h`，不碰 Pd 内部头
  （`m_imp.h`/`s_stuff.h`），也没有 autotools。
- 外部对象**故意不链接 libpd**：Pd API 符号在 `iemlib.pd_linux` 里保持
  undefined，由运行中的 `pd` 进程在装载时解析（`readelf -d` 只有
  `NEEDED = libc.so`）。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/pd-externals/iemlib.pd_linux` | 单个多对象外部库（约 78 个类） |
| `lib/pd-externals/help/*.pd` | 77 个帮助补丁 |
| `lib/pd-externals/abs/*.pd` | 165 个 abstraction + 134 个帮助补丁 |
| `lib/pd-externals/alias/*.pd` | 4 个别名补丁 |
| `lib/pd-externals/examples/*` | 示例补丁 |
| `licenses/LICENCE.txt`、`licenses/GnuLGPL.txt` | LGPL-2.1 |

## 参考资料

- 上游（.dsc 声明的 Homepage）：<https://git.iem.at/pd/iemlib>
- 取源：Debian 官方归档 `pd-iemlib_1.22.3.orig.tar.bz2`
- 许可证：LGPL-2.1-or-later
