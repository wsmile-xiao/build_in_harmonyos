# tnef 1.4.18 — HarmonyOS PC 适配说明

## 概况

`tnef` 解码 Microsoft TNEF（`winmail.dat`）附件。产物为 `bin/tnef` 与 man 手册。

- 上游：https://github.com/verdammelt/tnef
- 形态：autotools（maintainer 快照，无 `configure`）
- 依赖：无
- 许可证：GPL-2.0-or-later

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 无 `configure` | `autoreconf --force --install` 自举（避开老 config.sub，E007） |
| 2 | `config.guess` 猜不出 HarmonyOS | 显式 `--build=aarch64-linux-gnu` |
| 3 | `mktemp -d` 恒 0700，HMDFS 下不可写 | 复用知识库 **E011 / DRAFT-6507**：改 `umask 000 && mkdir` |
| 4 | BSD `rindex()` 无符号 | 复用知识库 **DRAFT-cconv-0.6.3-rindex-strrchr**：改 `strrchr()` |
| 5 | 上游测试假定 in-source | 在源码目录手动 configure/make/make check |
| 6 | CLI 工具门禁 | 软件级 `commands.json` |

## 测试

### 上游

`make check` 共执行 **29** 个 `.test` 脚本（`tests/cmdline` 14 个 + `tests/files` 15 个；取数 `find tests -name '*.test' -not -path '*/Attic/*'`）：其中 **27/27 PASS**（cmdline 12、files 15），另 2 个 `use-path`/`interactive` 为上游 `XFAIL_TESTS`（预期失败）。

### 消费者测试（test_package）

`test_package/test_tnef.sh` **3** 条断言：`--version`=1.4.18、`--help` 用法、缺失输入优雅失败。

## 已知限制

- `use-path`/`interactive` 为上游 `XFAIL_TESTS`（预期失败），已随 `make check` 执行，按要求不计入通过率。
- Windows/macOS 未验证（`validate()` 限定 Linux/OHOS）。
