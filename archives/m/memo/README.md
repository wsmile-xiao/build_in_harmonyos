# memo 1.7.1 — HarmonyOS PC 适配说明

## 概况

`memo` 是一个 Unix 风格的记事（note-taking）命令行工具，把 notes 追加到
`$HOME/.memo`（可用 `~/.memorc` 配置），支持添加/列出/搜索/标记完成/延后/导出等。

- 上游：https://www.nrosvall.name/memo/ （https://github.com/nrosvall/memo）
- 形态：单文件 C 程序（`memo.c`）+ 手写 Makefile
- 产物：`bin/memo`、`share/man/man1/memo.1`
- 依赖：无
- 许可证：GPL-3.0-or-later

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 单文件 C 程序 | 注入 OHOS clang 直接 `make`（仅 `-Wtautological-constant-out-of-range-compare` 告警，不影响功能） |
| 2 | 无上游测试套件 | 上游 Makefile 只有 all/clean/install/uninstall → rule4 N=0 不触发 |
| 3 | 构建环境无 `install(1)` | `package()` 手工拷贝 `bin/memo` 与 man |
| 4 | CLI 工具门禁 | 软件级 `commands.json` |

## 测试

### 上游

上游无测试套件（无 `make check`/`ctest`）。

### 消费者测试（test_package）

`test_package/test_memo.sh` 共 **3** 条断言，在临时 `HOME` 中真实运行安装后的 `memo`：

- `--version` 报告 `1.7.1`
- `--help` 打印 `SYNOPSIS`
- `-a "hello memo"` 添加、`-s` 列出，能读回该 note

## 已知限制

- Windows/macOS 未验证（`validate()` 限定 Linux/OHOS）。
