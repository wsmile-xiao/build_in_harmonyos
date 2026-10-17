# qfits 6.2.0 — HarmonyOS PC 适配说明

## 概况

`qfits` 是 ESO 的 FITS 文件读写 C 库，附带命令行工具。

- 上游：https://www.eso.org/sci/software/eclipse/qfits/
- 形态：autotools（2007 年，随包 `configure` + libtool）
- 产物：`lib/libqfits.so*`、`lib/libqfits.a`、`include/qfits.h` 等、`bin/`（11 个工具）、`share/man/man1/`（10 个）
- 工具：`dfits`、`dtfits`、`flipx`、`frameq`、`qextract`、`replacekey`（main）+ `fitsort`、`iofits`、`fitsmd5`、`hierarch28`、`stripfits`（saft）
- 依赖：无（链接 `-lm`）
- 许可证：GPL-2.0-or-later

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 随包 `admin/config.sub`（2004）不认 `aarch64`，且构建机只有 autoconf、缺 automake | `tool_requires("automake/1.18")`+`libtool/2.5.4` 注入 PATH，`autoreconf -fi -I m4macros`（`env="conanbuild"`）重新生成 configure/config.sub（对齐 abiword-plugin-* 先例） |
| 2 | autoconf 的 `configure`/`config.status` 用 `umask 077 && mktemp -d` 建暂存目录 | HMDFS 下 `drwx--S---` 不可写 → 去掉 `umask 077`（E114 / DRAFT-6507） |
| 3 | 设备 `uname` 返回 `HarmonyOS`，`config.guess` 猜不出三元组 | `configure` 显式传 `--build=aarch64-unknown-linux-ohos`；老 configure 探测 C++ 预处理器（默认 `/lib/cpp`）→ 一并传 `CXX`/`CPP` |
| 4 | 上游 `test/test_tfits.c` 的 `char filename[512]` 未初始化即 `strcat`（UB） | OHOS 上暴露为垃圾路径导致二进制表测试假失败 → 补丁初始化为 0（上游测试修改，见下） |
| 5 | `make install` 只装 `qfits.h`，但它 include 其余 `qfits_*.h` | `package()` 追加安装全部 `src/*.h`；并移除 libtool `.la` |
| 6 | CLI 工具门禁 | 软件级 `commands.json`；装 11 个工具 + man |

## 测试

### 上游

`make check` 运行 `test/` 下 5 个自包含 C 测试程序：**5/5 PASS**
（`test_pixio`、`test_qfits`、`test_tfits`、`test_xmem`、`test_xmem_stress`）。

### 消费者测试（test_package）

`test_package/test_qfits.c` 编译并运行一个程序，include 安装后的 `<qfits.h>` 并调用
`qfits_version()`，断言返回非空（实测 `QFITS_VERSION=6.2.0`），验证库可链接、公共头可用。

## 已知限制

- 工具未做端到端 FITS 处理验证（上游 `test/` 已覆盖库核心路径）。
- Windows/macOS 未验证（`validate()` 限定 Linux/OHOS）。
