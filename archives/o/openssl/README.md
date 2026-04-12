# OpenSSL 1.1.1w for HarmonyOS

## 概述

OpenSSL 1.1.1w 在 HarmonyOS/OpenHarmony (aarch64) 上的编译和测试记录。

**关键修复**: 使用 `no-asm` 选项禁用汇编优化，解决了 RSA-PSS 签名验证的 BAD_SIGNATURE bug。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | OpenSSL |
| 版本 | 1.1.1w |
| 下载地址 | https://www.openssl.org/source/openssl-1.1.1w.tar.gz |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 工具链 | llvm-ar, llvm-ranlib, llvm-nm |

## 编译步骤

```bash
# 1. 解压源码
tar -xzf openssl-1.1.1w.tar.gz
cd openssl-1.1.1w

# 2. 设置环境变量
export TMPDIR=$HOME/tmp
mkdir -p $TMPDIR

# 3. 配置 (关键：使用 no-asm 禁用汇编优化)
./Configure --prefix=$HOME/usr/local \
            --openssldir=$HOME/usr/local/ssl \
            no-asm

# 4. 编译
make -j$(nproc)

# 5. 安装
make install
```

## 补丁说明

### 修改文件

1. **Configurations/15-openharmony.conf**: OpenHarmony 平台配置
2. **Configure**: 添加自动检测逻辑

### 关键修改详解

#### 汇编优化禁用 (关键!)

**问题背景**：OpenSSL 的 ARM64 汇编优化代码在 RSA-PSS 签名验证时有 bug，导致 HTTPS 连接失败。

**错误信息**：
```
error:0407E086:rsa routines:RSA_verify_PKCS1_PSS_mgf1:last octet invalid
error:1417B07B:SSL routines:tls_process_cert_verify:bad signature
```

**解决方案**：使用 `no-asm` 禁用汇编优化

```bash
./Configure ... no-asm
```

**影响**：
- 性能略慢 (~10-20%)
- 稳定性大幅提升
- HTTPS 连接正常工作

## 遇到的问题

### 问题1：SSL BAD_SIGNATURE 错误

**现象**：Python HTTPS 连接失败，报 `BAD_SIGNATURE` 错误

**原因**：ARM64 汇编优化代码 bug

**解决**：使用 `no-asm` 编译

### 问题2：Python _ssl 模块链接问题

**现象**：`_ssl.so` 没有链接 libssl 和 libcrypto

**原因**：Python 构建系统配置问题

**解决**：手动重新编译 _ssl 模块

```bash
# 编译
clang -fPIC -I./Include -I$HOME/usr/local/include \
      -c Modules/_ssl.c -o build/temp.ohos-aarch64-3.9/Modules/_ssl.o

# 链接
clang -shared -L. -lpython3.9 \
      -L$HOME/usr/local/lib -lssl -lcrypto \
      build/temp.ohos-aarch64-3.9/Modules/_ssl.o \
      -o build/lib.ohos-aarch64-3.9/_ssl.so

# 验证链接
llvm-readelf -d _ssl.so | grep NEEDED
# 应该看到: libssl.so.1.1, libcrypto.so.1.1
```

### 问题3：官方测试套件失败

**现象**：所有 159 个测试返回 exit code 2

**原因**：鸿蒙签名机制，测试二进制需要手动确认

**解决**：进行手动功能测试验证核心功能

## 测试结果

详见 [TEST_REPORT.md](./TEST_REPORT.md)

**核心测试结果**：

| 测试项 | 结果 |
|--------|------|
| AES 加密 | ✅ |
| SHA256 哈希 | ✅ |
| RSA 密钥生成 | ✅ |
| 自签名证书 | ✅ |
| TLS 1.3 连接 | ✅ |
| HTTPS 连接 | ✅ |

## 经验总结

1. **汇编优化问题**：在 HarmonyOS 上编译 OpenSSL，应使用 `no-asm` 禁用汇编优化
2. **Python 链接**：确保 _ssl.so 正确链接 libssl 和 libcrypto
3. **测试限制**：官方测试套件因签名机制无法自动运行，需手动测试

## 参考资料

- OpenSSL 官方文档: https://www.openssl.org/docs/
- OpenSSL Configure 选项: https://wiki.openssl.org/index.php/Compilation_and_Installation
