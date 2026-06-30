# librelp

## 简介

librelp 是 RELP（Reliable Event Logging Protocol）协议的实现库，主要用于 rsyslog 的可靠日志传输。

## OHOS 适配

### 关键问题

1. **config.guess/config.sub 更新**：需要手动添加 HarmonyOS 支持。

2. **autoreconf 依赖**：补丁包含 autoreconf 生成的文件，G0 干净构建验证需要额外处理。

### 与 Linux 的差异

- Linux：标准 autotools 流程
- OHOS：需要手动更新 config.guess/config.sub

## 依赖

- gnutls（可选，用于 TLS 支持）

## 功能验证

```bash
pkg-config --modversion relp
```

## 参考

- 官网：https://www.rsyslog.com/librelp/