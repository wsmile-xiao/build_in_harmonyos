# gnupg 2.4.9.1 适配记录

本版本是对历史 2.4.9 失败记录的修复候选：保留 gpg 与 gpg-agent，关闭依赖 libksba、网络服务和文档的可选组件。

- 修复 config.guess/config.sub 的 OHOS 三元组识别。
- 使用 OHOS 最小配置，避免旧动态 libiconv 预编译包的运行时链接问题。
- 依赖 libgpg-error、libgcrypt、libassuan、npth 的已发布配方。
- test_package 验证 gpg、gpg-agent、gpgconf 的版本命令。

真实 OHOS CI 仍需确认 gpg-agent 的设备运行权限及 socket 行为；在 CI 通过前不标记为 built。
