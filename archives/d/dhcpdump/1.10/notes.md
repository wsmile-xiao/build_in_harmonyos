# dhcpdump 1.10 — HarmonyOS PC 适配记录

## 概述
dhcpdump 1.10 是一个简单的 DHCP 包解析工具，使用 Makefile 构建系统。
依赖 libpcap 进行网络包捕获。

## 适配过程

### 遇到的问题
1. **UDP header 字段不兼容**: HarmonyOS 的 `udphdr` 结构体使用 `uh_ulen`（BSD 风格）而非 `len`（Linux 风格），即使定义了 `__linux__`。R8 合规方案：通过 conanfile.py CPPFLAGS 注入 `-DUDP_LEN_F=uh_ulen` 宏定义，不在补丁中使用 `#ifdef __OHOS__`。
2. **缺少 install 目标**: 原始 Makefile 没有 install 目标，通过补丁添加。
3. **libpcap 依赖**: 需要链接 libpcap 库，通过 Conan 依赖管理。

### 补丁
- 0001-udp-len-f-portable.patch: 使 UDP_LEN_F 可通过 CPPFLAGS 覆盖，适配 OHOS udphdr.uh_ulen
- 0002-add-install-target.patch: 添加 Makefile install 目标

## 构建信息
- 构建系统: makefile
- 编译器: clang 15
- 架构: aarch64
- 平台: OHOS 6.0
---

**编译结束**: 2026-07-15 09:47
**最终状态**: failed
