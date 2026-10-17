# xe 1.0 — HarmonyOS PC 适配说明

## 概况

`xe` 是 xargs(1) 与 apply(1) 的现代替代：从 stdin/文件/argv 读取参数，
逐参数（或按 `-N` 批量、`-j` 并行）构造并执行命令，支持 `{}` 替换、
`-n` 干跑、`-s` shell 模式、`-0` NUL 分隔输入等。

- 上游：https://github.com/leahneukirchen/xe
- 形态：单文件 C 程序（`xe.c`），产物是 CLI 工具 `bin/xe`
- 依赖：无
- 许可证：CC0-1.0（公共领域）

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 单文件 C 程序 | 直接用 OHOS clang 编译（上游 flags：`-O2 -Wall -Wno-switch -Wextra -Wwrite-strings`），无需源码补丁 |
| 2 | 上游 TAP 测试 | `prove -v t` 运行 6 个 `.t` 脚本（共 63 条 TAP 断言）；`.t` 用 `PATH=.:$PATH` 找 `tap3`，并把 `xe` 加入 PATH |
| 3 | `t/simple.t` 的 `-A%` 用例依赖 GNU echo | OHOS 的 `echo` 把 `--` 当选项结束符（`echo -- 1` 只输出 `1`）→ 最小补丁把该用例命令改成 `printf`（不重解释 `--`），保留用例原意 |
| 4 | CLI 工具门禁 | 软件级 `commands.json`；装 `bin/xe` + man + zsh 补全 |

## 测试

### 上游

`t/` 下 6 个 TAP 脚本（`simple.t` 27、`errors.t` 16、`percent.t` 13、`slow.t` 4、
`limits.t` 2、`regressions.t` 1），共 **63** 条断言，`build()` 中 `prove -v t` 全部通过。

### 消费者测试（test_package）

`test_package/test_xe.sh` 共 **6** 条断言，真实运行安装后的 `bin/xe`：

- 默认逐行执行、`-N2` 批量、`-N0` 一次全传
- `{}` 占位替换
- `-0` NUL 分隔输入
- `-n` 干跑打印命令

## 已知限制

- 未验证 `-j` 并行在共享设备上的调度细节（上游 `simple.t` 已覆盖）。
- Windows/macOS 未验证（`validate()` 限定 Linux/OHOS）。
