# aws-lc 1.72.0 - OpenHarmony 预编译包

## 版本信息

- **软件**: AWS-LC (AWS Crypto Library)
- **版本**: 1.72.0
- **发布日期**: 2026-04-24
- **许可证**: OpenSSL/SSLeay/BSD-style

## 变更摘要

这是 aws-lc v1.72.0 版本的 OpenHarmony aarch64 预编译包。

主要特性:
- ML-KEM (Kyber) 后量子密码学支持
- ML-DSA 签名算法支持
- AES-GCM-SIV 认证加密
- 完整的 TLS 1.3 支持
- OpenSSL 1.1.1 API 兼容

## 编译配置

```bash
cmake -B build \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DDISABLE_GO=ON \
  -DOPENSSL_NO_ASM=1

cmake --build build -j$(nproc)
DESTDIR=$TEST_PREFIX cmake --install build --prefix=$DEFAULT_PREFIX
```

## 编译说明

1. **Go 依赖**: aws-lc 默认需要 Go 1.17+ 运行测试。使用 `-DDISABLE_GO=ON` 禁用 Go 依赖，使用预生成的代码。

2. **汇编优化**: CMake 无法识别 HarmonyOS 平台，导致汇编代码未编译。使用 `-DOPENSSL_NO_ASM=1` 使用纯 C 实现（性能略有下降）。

## 产物文件

- `aws-lc-1.72.0-ohos-aarch64.tar.gz` - 预编译包 (11493KB)
- `aws-lc-1.72.0-ohos-aarch64-debug.tar.gz` - 调试符号包 (947KB)
- `install-aws-lc-1.72.0.sh` - 安装脚本

## 包含内容

- `libcrypto.a` - 栓加密库 (静态)
- `libssl.a` - SSL/TLS 库 (静态)
- `bssl` - BoringSSL 命令行工具
- `openssl` - OpenSSL 兼容命令行工具
- OpenSSL API 头文件 (89 个)
- pkgconfig 文件

## 安装方法

```bash
./install-aws-lc-1.72.0.sh
```

或手动安装:
```bash
tar xzf aws-lc-1.72.0-ohos-aarch64.tar.gz -C $HOME/usr/local --strip-components=1
```

## 使用验证

```bash
bssl version  # 输出: 1.72.0
openssl version  # 输出: OpenSSL 1.1.1 (compatible; AWS-LC 1.72.0)
```

## 已知限制

- 无汇编优化（性能约下降 20-30%）
- 完整测试套件需要 Go 环境

## 质量状态

- G1 二进制完整性: PASS
- G2 功能可用性: PASS (bssl/openssl 验证)
- G3 可移植性: PASS (静态库无 RPATH 问题)
- G4 档案完整性: PASS
- G0 干净构建验证: PARTIAL (平台限制)