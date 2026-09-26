# sngrep

sngrep 是基于 ncurses 的 SIP 信令流查看器：支持从网卡/pcap 文件捕获 SIP 消息、重建通话流、TLS 解密（可选）等。

- 上游：https://github.com/irontec/sngrep
- 已适配版本：1.8.3（见 1.8.3/notes.md）
- 产物：CLI 工具 `sngrep`（交互式 TUI；脚本场景可用 -I 读 pcap + --dump 等非交互参数）
