# rtpengine

rtpengine 是 sipwise 开发的高性能媒体转换引擎（Sofia-SIP 生态），负责 RTP 媒体流的转发、转码（G.711/G.722/Opus/BCG729）、录音与 NAT 穿透。本仓库将其适配到 OpenHarmony PC（arm64），以 conan 包形式交付。

## 交付形态

- conan 包 `rtpengine/<版本>`（16 个已发布依赖 + perl tool_requires）
- 产物：3 个二进制（rtpengine 主守护进程 PIE / rtpengine-recording 录音守护进程 / rtpengine-perftest 压测工具）+ 3 个 perl 控制脚本（rtpengine-ctl / rtpengine-ng-client / rtpengine-get-table）+ librtpengine 静态库
- 命令行工具声明：`commands.json`（软件级）

## 版本

- `26.0.1.15` — 首次适配（上游 mr26.0.1.15）
