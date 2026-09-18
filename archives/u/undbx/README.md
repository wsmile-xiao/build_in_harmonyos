# UnDBX

UnDBX is a command-line tool that extracts, recovers, and undeletes email messages from Outlook Express `.dbx` files.

## 功能

- 从单个 DBX 文件或文件夹提取 `.eml` 消息。
- 支持恢复模式，尝试恢复损坏 DBX 中的消息片段。
- 支持安全文件名、忽略空消息和删除消息同步等命令行选项。

## HarmonyOS PC 适配

- 使用 Autotools 在 HarmonyOS PC arm64 native 环境构建。
- GitHub 源码快照不含 `configure`，构建时先运行 `autoreconf`。
- 生成的 `config.guess/config.sub` 在构建时补充 `aarch64-unknown-linux-ohos` 识别。
- HMDFS 上 Autoconf 临时目录使用组可写 umask，避免 UID 映射导致 `config.status` 无法写入。

## 依赖

无第三方 Conan 依赖；构建需要 clang、GNU make、Autoconf 和 Automake。

## 参考

- 上游仓库：[ZungBang/undbx](https://github.com/ZungBang/undbx)
- 许可证：GPL-3.0-or-later
