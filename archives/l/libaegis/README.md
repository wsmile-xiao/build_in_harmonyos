# libaegis

## 描述

Portable C implementations of the AEGIS family of high-performance authenticated encryption algorithms.

AEGIS 是一组高性能认证加密算法（AEAD），适用于高性能场景（如网络协议、存储加密）。
libaegis 提供纯 C 实现，不依赖外部库，支持多种 CPU 架构和 SIMD 加速。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.10.0 | built | 2026-06-17 |

## 构建信息

- **构建系统**: cmake
- **语言**: C99
- **编译器**: clang 15.0.4
- **依赖**: 无外部依赖
- **输出**: 静态库 `libaegis.a`

## 安装

```bash
# 使用预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libaegis 0.10.0

# 验证
ls ~/usr/local/lib/libaegis.a
ls ~/usr/local/include/aegis*.h
```

## 支持的算法

- **aegis128l**: 128-bit key, 128-bit nonce, 输出速率高
- **aegis256**: 256-bit key, 256-bit nonce, 更高安全性
- **aegis128x2 / aegis128x4**: 128-bit 变体的 SIMD 并行版本
- **aegis256x2 / aegis256x4**: 256-bit 变体的 SIMD 并行版本
- **RAF**: Random Access Format 文件加密格式
- **KDF**: 密钥派生函数 (aegis_kdf_128 / aegis_kdf_256)
