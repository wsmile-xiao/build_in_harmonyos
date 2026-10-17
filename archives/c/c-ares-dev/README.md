# c-ares-dev

c-ares 是一个 C 库，用于异步 DNS 请求（包括名称解析）。`c-ares-dev` 是 HarmonyOS 适配版本。

## 功能概述

- 异步 DNS 解析（A、AAAA、CNAME、MX、NS、TXT 等）
- 支持 IPv4 和 IPv6
- 多平台 C 库，被 curl、libcurl 等广泛使用
- 线程安全，事件驱动

## OHOS 适配

- 构建系统为 autotools，需要更新 config.guess/config.sub 以识别 HarmonyOS/ohos
- 需要 3 个平台适配补丁（config.guess + config.sub + configure umask fix）
- OHOS 无 GNU ld，需要显式 `LD=ld.lld` + `-fuse-ld=lld`

## 依赖关系

- 无外部编译依赖
- 可能依赖系统 libc 的 DNS 相关接口

## 参考资料

- 官网: https://c-ares.org/
- 源码: https://github.com/c-ares/c-ares
