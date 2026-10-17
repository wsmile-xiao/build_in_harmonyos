# memo 1.7.1 — HarmonyOS PC 适配说明

## 概况

`memo` 是 Unix 风格记事 CLI，notes 存于 `$HOME/.memo`。产物 `bin/memo` + man。

- 上游：https://www.nrosvall.name/memo/
- 形态：单文件 C（`memo.c`）+ Makefile
- 依赖：无
- 许可证：GPL-3.0-or-later

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 单文件 C | 注入 clang 直接 `make` |
| 2 | 无上游测试 | N=0，rule4 不触发 |
| 3 | 无 `install(1)` | `package()` 手工拷贝 |
| 4 | CLI 门禁 | 软件级 `commands.json` |

## 测试

### 上游

无测试套件。

### 消费者测试（test_package）

`test_package/test_memo.sh` **3** 条断言：`--version`=1.7.1、`--help` 含 SYNOPSIS、`-a`/`-s` 往返。

## 已知限制

- Windows/macOS 未验证（`validate()` 限定 Linux/OHOS）。
