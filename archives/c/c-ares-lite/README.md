# c-ares-lite

c-ares-lite 是 c-ares 异步 DNS 解析库（C 库）的轻量适配标识，官方来源为
c-ares 官方仓库 https://github.com/c-ares/c-ares 。

## 功能概述

- 异步 DNS 解析（A、AAAA、CNAME、MX、NS、TXT 等）
- 支持 IPv4 和 IPv6
- 多平台 C 库，被 curl、libcurl 等广泛使用
- 线程安全，事件驱动

## OHOS 适配

- 构建系统为 autotools，需要更新 config.guess/config.sub 以识别 HarmonyOS/ohos
- 参考 c-ares 1.34.6 历史归档：需 config.guess + config.sub + configure(umask 077, E129) 补丁

## 依赖关系

- 无外部编译依赖
- 可能依赖系统 libc 的 DNS 相关接口

## 参考资料

- 官网: https://c-ares.org/
- 源码: https://github.com/c-ares/c-ares