# libressl 4.3.1 — OpenHarmony 编译记录

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件 | libressl |
| 版本 | 4.3.1 |
| 状态 | ⚠️ partial（部分成功） |
| 构建系统 | cmake |
| 目标平台 | ohos-aarch64 |
| 编译日期 | 2026-04-24 |
| 源码路径 | https://ftp.openbsd.org/pub/OpenBSD/LibreSSL/libressl-4.3.1.tar.gz |

## 编译结果

### 编译产物

| 文件 | 大小 | 说明 |
|------|------|------|
| libcrypto.a | 3.1M | 核心加密算法库 |
| libssl.a | 629K | SSL/TLS 协议实现 |
| libtls.a | 111K | 简化 TLS API |

**注意**：未编译 `openssl` 命令行工具（LIBRESSL_APPS=OFF）

### 配置参数

```bash
cmake -B build \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DLIBRESSL_TESTS=OFF \
  -DLIBRESSL_APPS=OFF
```

- `LIBRESSL_TESTS=OFF`：禁用测试套件（避免测试依赖）
- `LIBRESSL_APPS=OFF`：禁用命令行工具（减少依赖）

## 编译指导

### 环境要求

- CMake >= 3.10
- C 编译器（支持 C99）
- aarch64 交叉编译工具链

### 完整编译步骤

```bash
# 1. 下载源码
wget https://ftp.openbsd.org/pub/OpenBSD/LibreSSL/libressl-4.3.1.tar.gz
tar xzf libressl-4.3.1.tar.gz
cd libressl-4.3.1

# 2. 手动复制架构头文件（必须步骤）
cp crypto/arch/aarch64/crypto_arch.h crypto/crypto_arch.h
cp crypto/bn/arch/aarch64/bn_arch.h crypto/bn/bn_arch.h

# 3. 配置
cmake -B build \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DLIBRESSL_TESTS=OFF \
  -DLIBRESSL_APPS=OFF

# 4. 编译
cmake --build build -j$(nproc)

# 5. 安装
cmake --install build --prefix $TEST_PREFIX
```

## 补丁清单

### 0001-config.guess.patch

**目的**：更新 config.guess 到最新版本（2025-07-10）

**修改内容**：
- 更新版权年份到 2025
- 添加 aarch64 架构检测优化
- 支持 Android libc 检测
- 添加新的 CPU 架构识别

**应用场景**：仅在使用 Autotools 构建时需要

### 0002-config.sub.patch

**目的**：更新 config.sub 到最新版本（2025-07-10）

**修改内容**：
- 更新版权年份到 2025
- 添加对新操作系统和架构的支持
- 改进配置字符串解析

**应用场景**：仅在使用 Autotools 构建时需要

**注意**：使用 CMake 构建时无需应用这些补丁。

## 已知限制

### 1. Autotools 在 HMDFS 上不可用

HMDFS 文件系统限制临时文件创建，导致 Autotools 构建失败：
- config.guess 无法在 $TMPDIR 创建临时文件
- configure 无法创建 config.status 临时文件

**解决方案**：使用 CMake 构建系统

### 2. 需手动复制架构头文件

CMake 构建系统未正确检测 OpenHarmony/aarch64 平台，需手动复制：
```bash
cp crypto/arch/aarch64/crypto_arch.h crypto/crypto_arch.h
cp crypto/bn/arch/aarch64/bn_arch.h crypto/bn/bn_arch.h
```

### 3. 无命令行工具

编译配置禁用了 `LIBRESSL_APPS`，因此未生成 `openssl` 命令行工具。如需命令行工具，修改配置：
```bash
-DLIBRESSL_APPS=ON
```

## 功能验证

### 静态库验证

```bash
# 检查库文件
ls -lh $TEST_PREFIX/lib/lib{crypto,ssl,tls}.a

# 输出示例：
# libcrypto.a  3.1M
# libssl.a     629K
# libtls.a     111K
```

### 符号表检查

```bash
# 检查加密函数
nm $TEST_PREFIX/lib/libcrypto.a | grep -E "AES_|RSA_|EVP_"

# 检查 SSL 函数
nm $TEST_PREFIX/lib/libssl.a | grep -E "SSL_|TLS_"
```

### 链接测试

```c
// test.c
#include <openssl/ssl.h>
#include <stdio.h>

int main() {
    printf("LibreSSL: %s\n", OPENSSL_VERSION_TEXT);
    return SSL_library_init();
}
```

```bash
${CC} -o test test.c \
  -I$TEST_PREFIX/include \
  -L$TEST_PREFIX/lib \
  -lssl -lcrypto -ltls \
  -static
```

## 相关文档

- [编译进度详情](./PROGRESS.md)
- [质量报告](./reports/quality-report.md)
- [测试报告](./reports/test-report.md)
- [SKILL 反馈](./reports/skill-feedback.md)