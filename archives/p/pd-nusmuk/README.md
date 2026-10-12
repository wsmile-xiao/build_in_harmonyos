# pd-nusmuk — Pure Data 外部对象集合（Cyrille Henry）

`pd-nusmuk` 是 Pure Data（Pd）的一组外部对象与抽象补丁，由 Cyrille Henry 编写，
以 GPL-2.0（仅 GPL-2.0 原文，无 or-later 授权）发布。上游分成两个库：

- **`nusmuk-utils`**（13 个外部对象）：`tab_max`、`tab_min`、`tab_integrate`、
  `tab_derivate`、`tab_upsample`、`tab_upsample_copy`、`tab_downsample`、
  `tab_downsample_max`、`tab_downsample_min`、`tab_downsample_average`、
  `line3`、`mtx_preset`、`pbank`。以 `table`/`array` 名字为构造参数，处理
  Pd 数组并从 outlet 发 completion bang；`line3` 是三次多项式斜坡发生器。
- **`nusmuk-audio`**（4 个外部对象）：`bq~`、`tabosc4c~`、`tabosci~`、
  `tabread4c~`。带限振荡器与更灵活的 table 读取，以及 biquad 滤波器。

另有 90 余个纯 Pd 抽象/帮助补丁（`between`、`lb`、`once`、`p`、
`mtx_presets` 相关等）、两个 meta 文件和 3 个 wav 采样。

## 用法

```sh
pd -path <pkg>/lib/pd-externals/nusmuk-utils:<pkg>/lib/pd-externals/nusmuk-audio
# 之后在补丁里直接使用 [tab_max src1 src2 dst]、[bq~]、[line3] 等
```

## OHOS 适配要点

- 上游用的是**老式 Pd `Makefile` 模板**（1.0.5 / 1.0.14），不是 `pd-lib-builder`。
  模板按 `$(uname -s)` 选目标，OHOS 上就是 `Linux`，因此自动选到
  `pd_linux` 扩展名和 `-fPIC`/`-shared` 链接参数——**无需为 OHOS 打补丁**。
- 模板把 `PD_INCLUDE` 写死成 `$(PD_PATH)/include`（Linux 分支 `PD_PATH=/usr`）。
  配方用 make **命令行赋值**盖掉它，指向 `pure-data 0.54-1` 源码树的 `src/`。
- `puredata/0.54.1` 是 application 包，**不装** `m_pd.h`（与
  `pd-maxlib`/`pd-mjlib` 同一结论），所以配方额外拉一份 pure-data 源码只取头。
- 不用 `make install`：它的 Linux 分支结尾调 `strip`，而 x86 构建机上的
  GNU strip 2.38 认不出 aarch64 ELF，会把构建拉挂。改为 `copy()` 直接打包。
- 产物只有 Pd 外部对象共享库，没有命令行可执行文件，因此不需要 `commands.json`。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/pd-externals/nusmuk-utils/*.pd_linux` | 13 个外部对象 |
| `lib/pd-externals/nusmuk-audio/*.pd_linux` | 4 个外部对象 |
| `lib/pd-externals/*/**.pd` | 抽象、帮助补丁、meta 文件 |
| `lib/pd-externals/*/*.wav`、`*/examples/` | 采样与示例 |
| `licenses/LICENSE.txt` | GPL-2.0 原文 |

## 参考资料

- 上游源码（Debian pool orig tarball）：
  <https://ftp.debian.org/debian/pool/main/p/pd-nusmuk/>
- Pure Data：<https://puredata.info>
- Pd `Makefile` 模板说明：<http://puredata.info/docs/developer/MakefileTemplate>