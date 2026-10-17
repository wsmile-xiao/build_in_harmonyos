# qrcp

qrcp — 纯 Go 编写的命令行工具，通过扫描二维码在电脑与移动设备之间经 Wi-Fi 传输文件，无需离开终端。

## 概述

qrcp 在电脑上启动一个临时 Web 服务器，并生成指向该服务器的二维码。手机扫码后即可下载（`qrcp send`）或上传（`qrcp receive`）文件。支持多网卡选择、HTTPS、反向二维码、ZIP 打包、配置文件等。

## 已编译版本

- **0.11.6** (2026-09-29) — Go 1.23.8, CGO_ENABLED=0, static build

## 关键信息

- **源码**: https://github.com/claudiodangelis/qrcp
- **构建系统**: Go（custom，根包 `go build .`；上游用 GoReleaser，无 Makefile/CMake/autotools）
- **依赖**: Go ≥ 1.18（go.mod 33 个依赖均为 Go module，无 C/C++ 第三方库）
- **平台**: linux/arm64 (HarmonyOS/OpenHarmony)

## 鸿蒙适配要点

1. 纯 Go 静态编译：`CGO_ENABLED=0`、`GOOS=linux`、`GOARCH=arm64`，无 cgo 依赖。
2. Go SDK 自引导：conanfile.py 下载 go1.23.8（官方 URL + sha256）到可写工作区。
3. Go linker mmap 在 HMDFS 上失败 → 链接输出放到 ext2 可写分区（`/data/storage/el2/base/haps/entry/files`）。
4. OHOS 上每个被 fork/exec 的 ELF 必须用 `binary-sign-tool` 自签名（含 `.codesign` 段），Go SDK 工具链、最终二进制与 `go test` 测试二进制同样需要。
5. HarmonyOS 沙箱限制 `AF_NETLINK`：`net.Interfaces()` 报 `netlinkrib: permission denied`。补丁使 `config.New()` 的接口探测失败告警而非 panic，调用方可用 `--interface` 显式指定网卡。

## 依赖关系

- **编译依赖**: Go 1.23.8 SDK（自动下载）；Go modules（由 `go.mod`/`go.sum` 锁定）
- **运行依赖**: 无（静态二进制，仅依赖内核接口）

## 参考资料

- **官网**: https://qrcp.sh
- **源码仓库**: https://github.com/claudiodangelis/qrcp
