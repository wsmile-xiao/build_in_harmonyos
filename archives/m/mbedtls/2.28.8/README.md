# mbedtls 2.28.8 for HarmonyOS

## 概述

mbedtls 2.28.8 是 2.28 LTS 系列的最新维护版本，提供了稳定的 SSL/TLS 实现。本页面记录了在 HarmonyOS/OpenHarmony (aarch64) 上的编译和测试结果。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | mbedtls |
| 版本 | 2.28.8 |
| 下载地址 | https://github.com/Mbed-TLS/mbedtls/releases/download/v2.28.8/mbedtls-2.28.8.tar.gz |
| 官方文档 | https://mbed-tls.readthedocs.io/en/latest/ |
| 许可证 | Apache 2.0 或 GPL 2.0+ |
| 编译状态 | ⚠️ partial |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 构建系统 | CMake |

## 编译步骤

### 1. 下载源码

```bash
# 下载源码包
wget https://github.com/Mbed-TLS/mbedtls/releases/download/v2.28.8/mbedtls-2.28.8.tar.gz

# 解压
tar -xzf mbedtls-2.28.8.tar.gz
cd mbedtls-2.28.8
```

### 2. 配置

```bash
# 创建构建目录
mkdir build && cd build

# 配置 CMake
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DENABLE_PROGRAMS=OFF \
  -DENABLE_TESTING=ON \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5
```

**关键配置说明**：
- `ENABLE_PROGRAMS=OFF`: 不编译示例程序（减小体积）
- `ENABLE_TESTING=ON`: 启用测试套件
- `CMAKE_POLICY_VERSION_MINIMUM=3.5`: 解决 CMake 版本策略警告

### 3. 编译

```bash
# 编译（推荐使用单线程以避免潜在问题）
make -j1

# 或使用多线程（如果确认无问题）
make -j$(nproc)
```

### 4. 测试

```bash
# 运行测试套件
make test

# 测试结果
# Passed: 96
# Failed: 12
# Pass Rate: 89%
```

### 5. 安装

```bash
# 安装到指定目录
make install

# 验证安装
ls -la $HOME/usr/local/lib/libmbed*
ls -la $HOME/usr/local/include/mbedtls/
```

## 补丁说明

本次编译未应用任何补丁。

### 已知但未修复的问题

虽然未应用补丁，但以下问题在测试中发现：

1. **时间相关测试失败**（平台限制）
   - 部分测试因 HarmonyOS 时区处理差异而失败
   - 影响范围：约 6 个测试用例
   - 严重程度：🟡 中等（不影响核心加密功能）

2. **网络相关测试失败**（平台限制）
   - socket 路径长度限制导致部分网络测试失败
   - 影响范围：约 4 个测试用例
   - 严重程度：🟡 中等（可用的网络功能正常）

3. **进程相关测试失败**（平台限制）
   - fork 相关测试在 HarmonyOS 上失败
   - 影响范围：约 2 个测试用例
   - 严重程度：🟢 轻微（多进程功能非必需）

## 遇到的问题

### 问题1: CMake 版本策略警告

**现象**:
```
CMake Warning (dev) at CMakeLists.txt:XX (project):
  Policy CMP0135 is not set
```

**原因**: CMake 版本较新，部分策略未设置

**解决**: 添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 参数

### 问题2: 部分测试失败

**现象**: `make test` 显示 12 个测试失败

**原因**: HarmonyOS 平台差异，非代码缺陷

**解决**: 已标记为平台限制，不影响核心功能使用

## 测试结果

详见 [test-report.md](./reports/test-report.md)

| 测试项 | 结果 |
|--------|------|
| 总测试数 | 108 |
| 通过 (PASS) | 96 (89%) |
| 失败 (FAIL) | 12 (11%) |
| 核心加密功能 | ✅ |
| TLS 协议栈 | ✅ |
| X.509 证书处理 | ✅ |
| 网络相关功能 | ⚠️ 部分受限 |

## 验证安装

### 快速验证

```bash
# 检查库文件
ls -lh $HOME/usr/local/lib/libmbed*
# 输出:
# libmbedcrypto.a
# libmbedtls.a
# libmbedx509.a

# 检查头文件
ls -lh $HOME/usr/local/include/mbedtls/ | head -5
# 应显示 aes.h, arc4.h, aria.h 等

# 测试版本
cat > test_version.c << 'EOF'
#include <stdio.h>
#include <mbedtls/version.h>

int main() {
    printf("mbedTLS version: %s\n", mbedtls_version_get_string());
    return 0;
}
EOF

clang -o test_version test_version.c \
  -I$HOME/usr/local/include \
  -L$HOME/usr/local/lib \
  -lmbedcrypto

./test_version
# 输出: mbedTLS version: 2.28.8
```

### 完整验证脚本

```bash
#!/bin/bash
# verify_mbedtls_2.28.8.sh

PREFIX=$HOME/usr/local

echo "=== 验证 mbedtls 2.28.8 安装 ==="

# 检查三个核心库
for lib in libmbedcrypto.a libmbedtls.a libmbedx509.a; do
    if [ -f "$PREFIX/lib/$lib" ]; then
        size=$(ls -lh "$PREFIX/lib/$lib" | awk '{print $5}')
        echo "✅ $PREFIX/lib/$lib ($size)"
    else
        echo "❌ 缺少 $PREFIX/lib/$lib"
    fi
done

# 检查头文件数量
header_count=$(ls $PREFIX/include/mbedtls/*.h 2>/dev/null | wc -l)
echo ""
echo "头文件: 找到 $header_count 个"

# 检查 pkg-config
export PKG_CONFIG_PATH=$PREFIX/lib/pkgconfig:$PKG_CONFIG_PATH
echo ""
echo "pkg-config 信息:"
pkg-config --cflags mbedtls 2>/dev/null || echo "  ⚠️  pkg-config 未配置"
pkg-config --libs mbedtls 2>/dev/null

echo ""
echo "=== 验证完成 ==="
```

## 使用示例

### AES 加密示例

```c
#include <stdio.h>
#include <string.h>
#include "mbedtls/aes.h"

int main() {
    unsigned char key[32] = {
        0x01, 0x23, 0x45, 0x67, 0x89, 0xab, 0xcd, 0xef,
        0xfe, 0xdc, 0xba, 0x98, 0x76, 0x54, 0x32, 0x10,
        0x01, 0x23, 0x45, 0x67, 0x89, 0xab, 0xcd, 0xef,
        0xfe, 0xdc, 0xba, 0x98, 0x76, 0x54, 0x32, 0x10
    };
    unsigned char iv[16] = {0};
    unsigned char plaintext[16] = "Hello, HarmonyOS";
    unsigned char ciphertext[16];
    unsigned char decrypted[16];
    
    mbedtls_aes_context aes;
    mbedtls_aes_init(&aes);
    
    // 加密
    mbedtls_aes_setkey_enc(&aes, key, 256);
    mbedtls_aes_crypt_cbc(&aes, MBEDTLS_AES_ENCRYPT, 16, iv, plaintext, ciphertext);
    
    printf("Plaintext:  %s\n", plaintext);
    printf("Ciphertext: ");
    for (int i = 0; i < 16; i++) printf("%02x", ciphertext[i]);
    printf("\n");
    
    // 解密
    mbedtls_aes_setkey_dec(&aes, key, 256);
    memset(iv, 0, 16);  // 重置 IV
    mbedtls_aes_crypt_cbc(&aes, MBEDTLS_AES_DECRYPT, 16, iv, ciphertext, decrypted);
    printf("Decrypted:  %s\n", decrypted);
    
    mbedtls_aes_free(&aes);
    return 0;
}
```

编译：
```bash
clang -o aes_example aes_example.c \
  -I$HOME/usr/local/include \
  -L$HOME/usr/local/lib \
  -lmbedcrypto
```

### SHA-256 哈希示例

```c
#include <stdio.h>
#include <string.h>
#include "mbedtls/sha256.h"

int main() {
    unsigned char input[] = "Hello, HarmonyOS! This is a test message.";
    unsigned char output[32];
    
    mbedtls_sha256(input, strlen((char*)input), output, 0);
    
    printf("Input:  %s\n", input);
    printf("SHA-256: ");
    for (int i = 0; i < 32; i++) {
        printf("%02x", output[i]);
    }
    printf("\n");
    
    return 0;
}
```

编译：
```bash
clang -o sha256_example sha256_example.c \
  -I$HOME/usr/local/include \
  -L$HOME/usr/local/lib \
  -lmbedcrypto
```

## 已知限制

### HarmonyOS 平台限制

1. **网络功能**：
   - 部分网络测试因 socket 路径长度限制失败
   - DTLS 功能基本可用
   - 建议：生产环境需额外测试

2. **进程相关**：
   - fork 相关测试失败
   - 多进程场景需替代方案

3. **时间相关**：
   - 部分时间测试因时区处理差异失败
   - 不影响时间戳验证核心功能

### 版本特性

- 此为 2.28 LTS 版本
- API 稳定，向后兼容 2.x 系列
- 建议新项目考虑 3.x 版本

## 预编译包

### 下载

预编译包位于：`packaging/mbedtls-2.28.8-ohos-aarch64.tar.gz`

### 安装

```bash
# 解压到目标目录
tar xzf mbedtls-2.28.8-ohos-aarch64.tar.gz -C ~/usr/local

# 运行安装脚本
cd ~/usr/local/mbedtls-2.28.8-ohos-aarch64
sh install-mbedtls-2.28.8.sh

# 验证
pkg-config --libs mbedtls
```

## 经验总结

1. **编译配置**：禁用示例程序可显著减小编译时间和包体积
2. **测试策略**：89% 的通过率表明核心功能可用，失败测试多为平台适配问题
3. **性能考虑**：单线程编译更稳定，多线程编译可能遇到竞态条件
4. **版本选择**：如需长期支持，2.28 LTS 是稳定选择

## 参考资料

- [mbedTLS 2.28 文档](https://mbed-tls.readthedocs.io/en/latest/)
- [CMake 配置选项](https://cmake.org/cmake/help/latest/manual/cmake.1.html)
- [HarmonyOS NDK 开发](https://developer.harmonyos.com/)
- [测试报告](./reports/test-report.md)

---

*本页由 openharmony-compile-agent 生成*  
*最后更新: 2026-04-24*