# liblxi

LXI (LAN eXtensions for Instrumentation) 兼容仪器的简洁 C 语言通信库。

- 主页: https://github.com/lxi-tools/liblxi
- 许可证: BSD-3-Clause
- 分类: 实用工具类
- 语言: C

## 描述

liblxi 提供简洁的 C 语言 API，用于与 LXI 兼容的测试测量仪器通信。支持 VXI-11 和 HiSLIP 协议进行设备通信，支持 mDNS 发现（需 avahi-client）。

## 可用版本

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.22 | published | 2026-06-12 | 无补丁，7/7功能测试通过 |

## 构建配置

- 构建系统: meson
- 必需依赖: libxml2 (≥2.x), libtirpc (≥1.x)
- 可选依赖: avahi-client（mDNS发现功能，平台不可用时自动禁用）
- 编译器: clang 15.0.4 / clang++

## 平台适配说明

- avahi-client 不可用 → mDNS 发现功能禁用（DISCOVER_MDNS模式无效）
- pthread_cancel: musl 不支持（vxi11.c编译警告，运行时如触发线程取消会失败）
- LD_LIBRARY_PATH: SDK llvm/lib 必须优先于 ~/usr/local/lib（E080: lld依赖SDK内置libxml2）
- 共享库需 ELF 签名才能在鸿蒙平台加载