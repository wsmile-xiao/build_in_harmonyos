# sntop

sntop（simple network top）是一个基于 ncurses 的终端网络主机连通性监视器。
它读取一份主机清单，周期性地对每个主机执行 `fping`（或退化为 `ping`），
并以 top 式界面把每个主机的 UP / DOWN 状态、备注一屏显示出来。

- 上游主页：<https://sntop.sourceforge.net/>
- 许可证：GPL-2.0-only
- 类型：命令行 / 终端交互工具（application，非库）

## 功能要点

- top 式彩色界面显示各主机状态与备注
- `-d` 守护模式（此时不进入 curses 界面）、`-o` 只轮询一次
- `-w` 生成 HTML 状态报表，`-e <file>` 指定报表路径
- `-a <脚本>` / `-l <脚本>` 在主机掉线 / 状态变化时执行外部脚本
- `-p` 改用 `ping`（默认 `fping`）、`-b <字节>` 调整探测包大小
- `-r <秒>` 调整轮询周期（默认 180 秒）、`-s` 安全模式（禁用交互命令）
- 配置优先读 `~/.sntoprc`，失败后回落编译期烧入的系统级路径

## 运行时依赖

sntop 自身不发包，它通过 `/bin/sh -c` 调用外部探测命令：

- 默认需要 **`fping`** 在 PATH 中（本机实测 `fping` 缺位时以退出码 6
  报 `sntop: error, execution of (f)ping failed`）；
- 加 `-p` 后改用 **`ping`**（HarmonyOS PC 上可用）。

## 本仓库版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 1.4.3 | built | 首个适配版本，见 `1.4.3/notes.md` |
