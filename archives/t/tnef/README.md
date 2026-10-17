# tnef 1.4.18 — HarmonyOS PC 适配说明

## 概况

`tnef` 解码 Microsoft TNEF（Transport Neutral Encapsulation Format，即
`winmail.dat`）附件并提取其中内嵌的文件。

- 上游：https://github.com/verdammelt/tnef
- 形态：autotools（发布包为 maintainer 快照，无生成的 `configure`）
- 产物：`bin/tnef`、`share/man/man1/tnef.1`
- 依赖：无
- 许可证：GPL-2.0-or-later

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 发布包无 `configure`（maintainer 快照），且构建机只有 autoconf、缺 `automake`/`aclocal` | `tool_requires("automake/1.18")`+`libtool/2.5.4`（对齐 abiword-plugin-* 先例）把工具注入 PATH，`autoreconf -fi`（`env="conanbuild"`）自举 |
| 2 | 设备 `uname` 返回 `HarmonyOS`，`config.guess` 猜不出三元组 | `configure` 显式传 `--build=aarch64-unknown-linux-ohos` |
| 3 | autoconf 的 `configure`/`config.status` 用 `umask 077 && mktemp -d` 建暂存目录 | HMDFS setgid 目录下 `drwx--S---` 不可写 → 去掉 `umask 077`（E114 / DRAFT-6507） |
| 4 | `src/path.c` 用 BSD 遗留函数 `rindex()` | OHOS libc 无该符号（链接失败）→ 复用知识库 **DRAFT-cconv-0.6.3-rindex-strrchr**：改用标准 `strrchr()` |
| 5 | 上游测试假定 in-source 构建 | baseline 内嵌 `./../../src/tnef` → 在源码目录手动 `configure`/`make`/`make check`，不用 conan 的 out-of-source Autotools |
| 6 | CLI 工具门禁 | 软件级 `commands.json`；装 `bin/tnef` + man |

## 测试

### 上游

`make check` 运行 automake 测试套件（自包含样本与 baseline）：

- `tests/cmdline`：**12/12 PASS**（help/version/basic/debug/list/verbose/overwrite/directory/maxsize/body/mime-types/stdin）
- `tests/files`：**15/15 PASS**（one-file/rtf/two-files/…/unicode-mapi-attr-name）

合计 **27/27**。

### 消费者测试（test_package）

`test_package/test_tnef.sh` 共 **3** 条断言，真实运行安装后的 `bin/tnef`：

- `--version` 报告 `1.4.18`
- `--help` 打印用法
- 缺失输入文件时优雅失败（非 0，不崩溃）

## 已知限制

- 上游 `use-path`/`interactive` 两个用例标记为 XFAIL（上游自身预期失败），未计入。
- Windows/macOS 未验证（`validate()` 限定 Linux/OHOS）。
