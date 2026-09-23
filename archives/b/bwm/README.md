# bwm

轻量控制台带宽监控命令行工具（Bandwidth Monitor）。

- 上游：https://github.com/vgropp/bwm-ng（tag v0.6.3）
- 主页：https://www.gropp.org/?id=projects&sub=bwm-ng
- 许可证：GPL-2.0-only
- 类型：命令行工具（tool）

## 功能概述

- 实时显示各网卡收发速率
- 支持 plain / csv 等文本输出
- 可选 curses 界面（本适配关闭）

## OHOS 适配

- 关闭 curses/ncurses，避免 ncurses 开发依赖；保留 `--help` / `--version` / `-o plain` / `-o csv`。
- 输入源使用 `/proc/net/dev`（`--with-proc-netdev`）。
- 静态链接（R26），产物 `bin/bwm`（及别名 `bin/bwm-ng`）无 `NEEDED` 动态库。
- `config.guess`/`config.sub` 在 autoreconf 之后打 HarmonyOS 识别补丁（E007），不传 `--build`/`--host`（R15）。
- 构建工具通过 Conan `tool_requires`（automake/1.18、libtool/2.5.4）引入，不硬编码本机路径。
- 上游无测试套件；`make check` 为 automake 默认 no-op，按 `no_tests` 口径输出 HMBS 标记，消费者测试在 `test_package/`。

## 依赖

- 编译：Autotools（autoconf + automake）；无外部 Conan 依赖
- 运行：静态链接，无额外动态库

## 参考

- 源码仓库：https://github.com/vgropp/bwm-ng
- 各版本详情见 `0.6.3/notes.md`
