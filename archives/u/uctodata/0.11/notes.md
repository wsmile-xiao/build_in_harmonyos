# uctodata 0.11 适配笔记

## 概述

将 Language Machines 的 `uctodata`（Radboud 大学奈梅亨 CLST 出品）适配为
HarmonyOS PC 的 Conan **纯数据包**。它提供 `ucto` 分词器所需的全部数据文件：
各语言的分词配置、缩写表、切分规则、引号/句尾表与连字符过滤表。

上游 README 明确写着 "uctodata is architecture independent"，因此本包
不声明 `settings`，包 ID 与 profile 无关（与 `adwaita-fonts-mono`、`festvox-*` 一致）。

## 安装内容

严格复刻上游 `config/Makefile.am` 中 `config_DATA` 的 **35 个文件**（17 + 10 + 3 + 5）：

| 分组 | 数量 | 示例 |
|---|---|---|
| `tokconfig-<lang>` / 变体 | 17 | `tokconfig-nld`、`tokconfig-eng-twitter`、`tokconfig-nld-sonarchat`、`tokconfig-generic` |
| 缩写表 `*.abr` | 10 | `nld_afk.abr`、`eng.abr`、`deu.abr`、`fry.abr` |
| 切分规则 `*.rule` | 3 | `e-mail.rule`、`smiley.rule`、`url.rule` |
| 引号/句尾/过滤器 | 5 | `standard-quotes.quote`、`exotic-eos.eos`、`ligatures.filter` |

安装目录：

- `share/ucto/` ← 上述 35 个数据文件（上游 `configdir = $(datadir)/ucto`）
- `lib/pkgconfig/uctodata.pc` ← 由配方生成（上游 `pkgconfigdir = $(libdir)/pkgconfig`）
- `licenses/` ← `AUTHORS`、`README.md`

## 为什么不走 autotools

上游是 autotools 工程，但 `configure.ac` 只做三件事：生成 `config/Makefile`、
生成 `uctodata.pc`、`AC_OUTPUT`。**没有任何编译步骤**（`config/Makefile.am` 只有
`config_DATA` / `EXTRA_DIST`）。

为它跑一次 `autoreconf -fi` 需要完整的 automake/libtool 工具链，收益为零，还要额外
打 `config.guess`/`config.sub` 补丁。配方改为直接复刻 `make install-data` 的行为：
按名字逐个 `copy` 那 35 个文件（**不**用通配符，避免把 `Makefile.am` 一起装进产物）。

## 关键点：pkg-config 是数据目录的唯一契约

`ucto` 自己的 `configure.ac` 是这么找数据的：

```m4
UCTODATA_PRE=`pkg-config --variable=prefix uctodata`
UCTODATA_DIR=$UCTODATA_PRE/share/ucto
AC_DEFINE_UNQUOTED([UCTODATA_DIR], ["$UCTODATA_DIR/"])
```

所以 `uctodata.pc` 里的 `prefix` **必须**指向本包的 `package_folder`。上游的
`uctodata.pc.in` 里是 `prefix=@prefix@`，直接拷贝会留下一串未展开的占位符，
消费方 configure 会走到 `ucto datafiles are not installed!` 的报错分支。

配方因此用 `package_folder` 现写一份 `.pc`，而不是复制模板。`test_package` 里有一条
断言专门守这个契约：如果环境里有 `pkg-config`，就直接执行
`pkg-config --variable=prefix uctodata` 并要求结果等于 `package_folder`。

## 完整性断言的写法

`build()` 里按上游 `config_DATA` **逐字列举** 35 个文件，并检查非空。
不要用"每种语言一个 `.abr`"这类推断：上游存在 `tokconfig-ita` 却没有 `ita.abr`，
荷兰语的缩写表叫 `nld_afk.abr` 而不是 `nld.abr` —— 按推断写会永远过不了自己的检查。

`test_package` 里同时断言 `Makefile.am` **没有**被装进产物，防止后续有人把
逐文件 `copy` 改回通配符。

## 上游测试情况

上游是纯数据包，tarball 里没有源码，也没有 `check`/`test` 目标，
`config/Makefile.am` 只有 `install-data`：**上游自动化用例数 = 0**。
所有验证在 `test_package/test_data.py`（19 条断言）中完成，覆盖：
pkg-config 契约、35 个数据文件齐全且非空、产物不带构建系统文件、
`tokconfig-nld` 的 `%include` 目标自洽性。

## 验证结果

- 编译状态：通过（无编译步骤，`conan create` 直接打包）
- 上游测试用例通过率：不适用（上游 0 个用例）
- 新增测试用例通过率：19/19（100%）
- 门禁：G0–G4 全绿，L2/L4/L5 全绿（`ohc-run.py conan-verify uctodata 0.11`）

## 来源

- Source URL: `https://github.com/LanguageMachines/uctodata/archive/refs/tags/v0.11.tar.gz`
- sha256: `e0d3bda7a73681526ac67318ddcc88798c524bb7c0f0daf6237cf2d4d3df2f12`
- 上游仓库: <https://github.com/LanguageMachines/uctodata>
- 许可证: GPL-3.0-or-later
