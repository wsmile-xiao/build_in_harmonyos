# sic 1.3 — HarmonyOS PC 适配说明

## 概况

`sic` 是 suckless 的**极简 IRC 客户端**（约 250 行 C）：从标准输入读取命令、
把所有频道流量多路复用到标准输出，连接后发送 `NICK`/`USER` 注册、应答服务器
`PING` 并转发 `PRIVMSG`。

- 上游：https://tools.suckless.org/sic/（源码仓库 https://git.suckless.org/sic）
- 形态：单源文件 `sic.c`（内部 `#include` `strlcpy.c`、`util.c`），产物是 CLI 工具 `bin/sic`
- 依赖：无（仅 libc；`config.h` 由上游 Makefile 从 `config.def.h` 生成）
- 许可证：MIT/X

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 单文件 C、无依赖 | 用上游 `Makefile` 构建；在 make 命令行注入 OHOS 工具链的 clang（`tools.build:compiler_executables`） |
| 2 | `config.h` 需从 `config.def.h` 生成 | 上游 Makefile 的 `config.h` 规则自动 `cp`，无需补丁 |
| 3 | 需要 `strlcpy` | 上游随包提供 `strlcpy.c` 并由 `sic.c` 直接 `#include`，不依赖 libc |
| 4 | 上游无任何测试 | `test_package/test_sic.sh` 补全消费者测试：真跑安装后的 `bin/sic`，并用本地 TCP 服务器完成一次 IRC 注册握手 |
| 5 | CLI 工具门禁 | 软件级 `commands.json`；装 `bin/sic` + `share/man/man1/sic.1` |

## 测试

### 上游

上游发布包**不含任何测试**（无 `tests/`、无 `make check`），故上游 N=0，
按规则在 `test_package` 中补全消费者测试。

### 消费者测试（test_package）

`test_package/test_sic.sh` 共 **6** 条断言，真实运行安装后的 `bin/sic`：

- `-v` 打印版本横幅 `sic-1.3, …`（上游经 `eprint` 输出并退出 1，属设计行为）
- 未知选项打印 `usage: sic …`
- 连接失败路径：`-h 127.0.0.1 -p 1` 报 `cannot connect to host`
- 对本地 IRC 服务器（`sic_ircsrv.py`）完成注册握手：捕获到 `NICK consumertest`
- 同上：捕获到 `USER consumertest`
- 服务器 `PING` 后客户端回 `PONG`

## 已知限制

- `sic` 无配置文件、无 GUI；`config.h` 采用上游默认（`DEFAULT_HOST irc.oftc.net`）。
- 消费者测试的握手服务器端口在 `41000–56000` 区间按 `$$` 选取。
- Windows/macOS 未验证（`validate()` 限定 Linux/OHOS）。
