# qfits 6.2.0 — HarmonyOS PC 适配说明

## 概况

`qfits` 是 ESO 的 FITS 文件读写库，附 11 个命令行工具。

- 上游：https://www.eso.org/sci/software/eclipse/qfits/
- 形态：autotools（2007）+ libtool
- 依赖：无（`-lm`）
- 许可证：GPL-2.0-or-later

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 老 `config.sub` 不认 aarch64，且构建机只有 autoconf、缺 automake | `tool_requires("automake/1.18")`+`libtool/2.5.4` + `autoreconf -fi -I m4macros`（env=conanbuild；abiword-plugin-* 先例） |
| 2 | `umask 077 && mktemp -d`，HMDFS 下不可写 | 去掉 `umask 077`（E114 / DRAFT-6507） |
| 3 | `config.guess` 猜不出 HarmonyOS | 显式 `--build=aarch64-unknown-linux-ohos`；老 configure 探测 C++ 预处理器 → 传 `CXX`/`CPP` |
| 4 | `test_tfits.c` 未初始化 `filename[512]` 即 strcat（UB） | 补丁初始化为 0（上游测试修改） |
| 5 | `make install` 只装 `qfits.h` | 追加安装 `src/*.h`；移除 `.la` |
| 6 | CLI 工具门禁 | 软件级 `commands.json` |

## 测试

### 上游

`make check`：`test_pixio`/`test_qfits`/`test_tfits`/`test_xmem`/`test_xmem_stress` **5/5 PASS**。

### 消费者测试（test_package）

`test_package/test_qfits.c`：include `<qfits.h>` 并调用 `qfits_version()`（返回 `6.2.0`）。

## 已知限制

- 工具未做端到端 FITS 处理验证。
- Windows/macOS 未验证（`validate()` 限定 Linux/OHOS）。
