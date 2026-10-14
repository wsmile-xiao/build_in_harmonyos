# typioca

Cozy terminal typing-speed tester —— 纯 Go 编写的终端打字速度测试工具，基于 [bubbletea](https://github.com/charmbracelet/bubbletea) TUI 框架，提供单词/句子词表、键盘布局切换、成绩统计及 SSH `serve` 模式。

## 功能概述

- 交互式打字测试（WPM/准确率统计），内嵌多套词表（Common words、Frankenstein、Dracula、Sherlock Holmes 等）与句子词表
- 键盘布局支持：Qwerty、Dvorak、Colemak DH、Gallium
- 本地成绩记录（results-io）
- `typioca serve`：以 SSH 服务形式对外提供打字测试服务
- `typioca completion`：生成 shell 自动补全脚本

## 已编译版本

- **3.1.0** (2026-10-12) — Go 1.26.5, CGO_ENABLED=0, 静态构建（aarch64）

## 关键信息

- **源码**: https://github.com/bloznelis/typioca
- **构建系统**: Go (custom，根包 `go build .`，上游 Makefile `make build` 的等价命令)
- **依赖**: Go ≥ 1.22.1（go.mod 声明；本适配使用 1.26.5）
- **平台**: linux/arm64 (HarmonyOS / OpenHarmony PC)

## 鸿蒙适配要点

1. **纯 Go 静态编译**：CGO_ENABLED=0、GOOS=linux、GOARCH=arm64，无 cgo 依赖
2. **HMDFS 链接规避**：Go 链接器对输出文件调用 `fallocate()`，HMDFS/tmpfs 返回 `EACCES`（`mapping output file failed: permission denied`，见知识 E523/E134）→ 链接输出放到 ext2 可写分区 `/data/storage/el2/base/haps/entry/files`
3. **ELF 签名**：OHOS 上每个被 `fork/exec` 的 ELF 必须用 `binary-sign-tool` 自签名（含 `.codesign` section），Go SDK 工具链同样需要签名
4. **Go 模块获取**：Go 的 netgo 解析器只读 `/etc/resolv.conf`，OHOS 开发镜像上其 nameserver 不可达 → 配方 `GOPROXY` 支持环境变量覆盖（本地用 `file://` 模块代理，CI 用 `https://goproxy.cn` 公共代理）
5. 上游 3.1.0 **无任何自动化测试**（无 `*_test.go`、Makefile 无 test 目标、CI 仅构建）；本适配新增消费者冒烟测试与鸿蒙签名断言

## 依赖关系

- **编译依赖**: Go 1.26.5 SDK（本地未找到时自动从 golang.google.cn / mirrors.aliyun.com / dl.google.com 下载并签名）
- **运行依赖**: 无（静态二进制，仅依赖内核/libc 接口）

## 已知限制

- 交互式 TUI 需要可用的终端；无 TTY 时会话不可用
- 词表同步与 `serve` 模式依赖网络；在 resolver 配置异常的设备上前者可能失败（运行时环境项，非构建阻塞）

## 参考资料

- **源码仓库**: https://github.com/bloznelis/typioca
- **Release 3.1.0**: https://github.com/bloznelis/typioca/releases/tag/3.1.0
