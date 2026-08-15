# shpotify

shpotify — "A command-line interface to Spotify". A simple Bash script to
control Spotify from the command line.

- Homepage: https://github.com/hnarayanan/shpotify
- Pure Bash script tool (no C compilation, no build system)
- Runtime needs Bash and common coreutils (curl/base64/grep/sed/tr)
- Installs the `spotify` command
- License: MIT

> 注意：上游 playback/search 子命令通过 macOS osascript 控制 Spotify 桌面
> 应用，属 macOS 平台设计。OHOS PC 上可运行入口为无参数调用（打印用法，
> 退出码 0）。
