# libressl — OpenHarmony 编译记录

## 软件简介

LibreSSL 是 OpenBSD 项目的 SSL/TLS 加密库分支，从 OpenSSL 1.0.1g 分支而来。它提供：
- **libcrypto**：加密算法库（对称加密、非对称加密、哈希算法等）
- **libssl**：SSL/TLS 协议实现
- **libtls**：简化的 TLS API 接口

LibreSSL 注重安全性、代码简洁性和现代化，移除了大量遗留代码和不安全特性。

## 构建系统

LibreSSL 支持两种构建系统：
- **CMake**（推荐）：现代构建系统，支持跨平台编译
- **Autotools**：传统构建系统，在 HMDFS 文件系统上有临时文件权限问题

## 编译指导

### 推荐配置（CMake）

```bash
# 配置
cmake -B build \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DLIBRESSL_TESTS=OFF \
  -DLIBRESSL_APPS=OFF

# 编译
cmake --build build -j$(nproc)

# 安装
cmake --install build --prefix $TEST_PREFIX
```

### 关键配置选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `LIBRESSL_TESTS` | 编译测试套件 | ON |
| `LIBRESSL_APPS` | 编译命令行工具（openssl） | ON |
| `LIBRESSL_EXAMPLES` | 编译示例程序 | ON |

对于 OpenHarmony 交叉编译，建议禁用测试和示例以减少依赖。

## 补丁清单

### 通用补丁

| 补丁文件 | 目的 |
|----------|------|
| `0001-config.guess.patch` | 更新 config.guess 到最新版本（2025-07-10），支持新平台识别 |
| `0002-config.sub.patch` | 更新 config.sub 到最新版本（2025-07-10），支持新平台配置 |

### 补丁应用方式

```bash
# Autotools 构建时应用
patch -p1 < patches/0001-config.guess.patch
patch -p1 < patches/0002-config.sub.patch
```

**注意**：使用 CMake 构建时无需应用这些补丁，因为 CMake 不依赖 config.guess/config.sub。

## 已知限制

### 1. HMDFS 文件系统权限问题（Autotools）

**症状**：使用 Autotools 构建时，config.guess 无法在 `$TMPDIR` 创建临时文件，configure 无法创建 config.status 临时文件。

**错误示例**：
```
./config.guess: cannot create temp file in /tmp
configure: error: could not create config.status
```

**原因**：HMDFS（HarmonyOS Distributed File System）对临时文件创建有特殊限制。

**解决方案**：使用 CMake 构建系统替代 Autotools。

### 2. 架构特定头文件缺失（CMake）

**症状**：CMake 编译时缺少 `crypto_arch.h` 和 `bn_arch.h`。

**错误示例**：
```
fatal error: crypto/crypto_arch.h: No such file or directory
fatal error: crypto/bn/bn_arch.h: No such file or directory
```

**原因**：CMake 构建系统的平台检测逻辑未正确识别 OpenHarmony/aarch64。

**解决方案**：手动复制架构特定头文件：
```bash
cp crypto/arch/aarch64/crypto_arch.h crypto/crypto_arch.h
cp crypto/bn/arch/aarch64/bn_arch.h crypto/bn/bn_arch.h
```

### 3. 静态库限制

LibreSSL 默认编译静态库和共享库。当禁用测试和应用程序时：
- ✅ 可编译：`libcrypto.a`, `libssl.a`, `libtls.a`
- ❌ 不可用：`openssl` 命令行工具（需启用 `LIBRESSL_APPS=ON`）

## 功能验证

### 静态库验证

```bash
# 检查库文件存在
ls -lh $TEST_PREFIX/lib/lib{crypto,ssl,tls}.a

# 检查符号表
nm $TEST_PREFIX/lib/libcrypto.a | grep -E "AES_|RSA_"

# 验证架构
file $TEST_PREFIX/lib/libcrypto.a
# 预期输出：... aarch64 ...
```

### 头文件验证

```bash
# 检查关键头文件
ls -lh $TEST_PREFIX/include/openssl/{ssl,tls,evp,aes}.h

# 验证头文件内容
grep -r "LIBRESSL_VERSION_TEXT" $TEST_PREFIX/include/openssl/
```

### 编译测试程序

创建测试文件 `test_libressl.c`：

```c
#include <openssl/ssl.h>
#include <stdio.h>

int main() {
    printf("LibreSSL version: %s\n", OPENSSL_VERSION_TEXT);
    printf("SSL library initialized: %s\n", 
           SSL_library_init() ? "success" : "failed");
    return 0;
}
```

编译并运行：
```bash
# 静态链接编译
${CC} -o test_libressl test_libressl.c \
  -I$TEST_PREFIX/include \
  -L$TEST_PREFIX/lib \
  -lssl -lcrypto -ltls \
  -static

# 在目标设备运行
./test_libressl
```

## 可用版本

| 版本 | 状态 | 构建系统 | 补丁数 | 备注 |
|------|------|----------|--------|------|
| 4.3.1 | partial | cmake | 2 | 仅静态库，无命令行工具 |

## 依赖关系

LibreSSL 无外部依赖，是底层加密库，可被以下软件依赖：
- curl（HTTPS 支持）
- wget（HTTPS 支持）
- git（HTTPS 支持）
- openssh（加密通道）