# otp 1.2.2 — HarmonyOS PC 适配说明

## 概况

`otp` 是 John Walker（fourmilab）的**一次性密码本 / 密码列表生成器**：
可生成随机字母、数字，或按英语字母二元组频率生成的“易记”口令；并可将每个
口令的 MD5 签名写入文件，便于应用在不保存明文口令的前提下校验口令。

- 上游：https://www.fourmilab.ch/onetime/
- 形态：纯 C，三个源文件（`otp.c`、`md5.c`、`random.c`），产物是 CLI 工具 `bin/otp`
- 依赖：无
- 许可证：Public Domain（源码头部声明）

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 上游 `Makefile` 硬编码 `CC = gcc` | 在 make 命令行覆盖 `CC`，指向 OHOS 工具链的 clang（`tools.build:compiler_executables`） |
| 2 | 无三方依赖、纯 C | 直接 `make`，无需源码补丁；`unix` 分支预定义宏由 clang 自动提供 |
| 3 | 上游自带确定性回归套件 | `build()` 中执行 `sh test.sh`（5 次固定种子的 `./otp` 调用）并 `diff test.mas test.out` 与金标准比对 |
| 4 | `test.sh` 依赖可执行位 | 通过 `sh test.sh` 调用，避免解压后丢失可执行位 |
| 5 | CLI 工具门禁 | 软件级 `commands.json`；装 `bin/otp` + `share/man/man1/otp.1` |

## 测试

### 上游

`test.sh` 用固定种子 `-rTEST` 执行 5 组 `./otp`（默认小写字母 / `-c12` / `-e12`
/ `-S5 -e -c` / `-d4`），并写出各自的 `-m` MD5 签名文件；`make check` 再把
拼接结果与金标准 `test.mas` 逐字节 `diff`。本配方在 `build()` 中复现同样的
5 次运行 + 1 次 `diff`，共 **6** 项检查全部通过。

### 消费者测试（test_package）

`test_package/test_otp.sh` 共 **4** 条断言，真实运行安装后的 `bin/otp`：

- `-U` 打印生成器横幅
- `-rTEST -n4` 输出确定的小写字母口令列表
- `-rTEST -n4 -m` 写出确定的 MD5 签名（首行 `04AE…3D48`）
- `-rTEST -n7 -d4` 输出确定的 4 位数字口令列表

## 已知限制

- 未使用 `-r` 时的种子依赖系统熵（`/dev/random` 等）；本沙箱上若 `/dev/random`
  不可用，代码在检测到读取失败时打印提示但不中止（此时仍用时间/pid 等熵）。
  消费者测试只用固定种子路径，保证确定性。
- Windows/macOS 未验证（`validate()` 限定 Linux/OHOS）。
