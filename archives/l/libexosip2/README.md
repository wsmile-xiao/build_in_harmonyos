# libexosip2

The eXtended osip library (libeXosip2) is an extension of the osip2 library, providing a higher-level API for SIP (Session Initiation Protocol) operations. It simplifies SIP transaction handling for applications such as VoIP clients and SIP proxies.

## Key Features

- SIP registration, call, message, subscription, and publication APIs
- TLS/DTLS/UDP/TCP transport support
- OpenSSL integration for secure communications
- Automatic transaction management (INVITE, REGISTER, BYE, etc.)
- Event-driven architecture with eXosip_event API

## Dependencies

- **libosip2 >= 5.0** (SIP parser and state machine) — 必需依赖
- **OpenSSL >= 1.1.1** (TLS/DTLS support) — 必需依赖
- **c-ares** (optional, DNS resolution) — 可选依赖，未安装不影响编译

## Platform Notes (HarmonyOS/OpenHarmony)

### 补丁说明

| 补丁 | 说明 | 类型 |
|------|------|------|
| 0001-configure.patch | umask 077→022 (HMDFS 权限兼容, E011) | platform_only |
| 0002-scripts-config.guess.patch | 替换为 2023 版 config.guess (含 HarmonyOS 识别, E072) | platform_only |
| 0003-scripts-config.sub.patch | 替换为 2023 版 config.sub (含 ohos 三元组) | platform_only |

### 构建说明

- 构建系统: autotools
- configure 选项: `--prefix=$DEFAULT_PREFIX` (仅 prefix，无 --build/--host/--target，遵循 R15)
- 平台识别: aarch64-unknown-linux-ohos (config.guess 自动识别)
- 预编译包 RUNPATH: `$ORIGIN:$ORIGIN/external` (相对路径，可移植)

### 测试状态

- **上游测试**: N/A（库无内置 make check 测试套件）
- **功能测试**: 40/40 全部通过 (100%) — 涵盖初始化、SIP 消息解析、REGISTER/INVITE 构造、序列化、URI 解析、SDP 解析、资源清理

### 已知限制

- sip_reg/sip_monitor/sip_storm 示例程序在 EXCLUDE_LIST 中（可能依赖网络环境，不适合本地测试）
- 无 pkg-config (.pc) 文件（上游不生成）

## Available Versions

- 5.3.0 (published, 2026-06-03)