# mbedtls 3.6.6 for HarmonyOS

## 概述

mbedtls 3.6.6 是 mbedtls 3.6 LTS 系列的最新版本，提供了现代化的 SSL/TLS 实现。本页面记录了在 HarmonyOS/OpenHarmony (aarch64) 上的编译和测试结果。

**重要提示**：mbedtls 3.x 相比 2.x 有重大 API 变化，请参考迁移指南。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | mbedtls |
| 版本 | 3.6.6 |
| 下载地址 | https://github.com/Mbed-TLS/mbedtls/releases/download/mbedtls-3.6.6/mbedtls-3.6.6.tar.bz2 |
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
# 下载源码包（注意：3.x 版本使用 .tar.bz2 格式）
wget https://github.com/Mbed-TLS/mbedtls/releases/download/mbedtls-3.6.6/mbedtls-3.6.6.tar.bz2

# 解压
tar -xjf mbedtls-3.6.6.tar.bz2
cd mbedtls-3.6.6
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
  -DENABLE_TESTING=ON
```

**关键配置说明**：
- `ENABLE_PROGRAMS=OFF`: 不编译示例程序（减小体积）
- `ENABLE_TESTING=ON`: 启用测试套件
- 3.x 版本不需要 `CMAKE_POLICY_VERSION_MINIMUM` 参数

### 3. 编译

```bash
# 编译（推荐使用多线程）
make -j$(nproc)
```

### 4. 测试

```bash
# 运行测试套件
make test

# 测试结果待补充
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

### 已知问题

待测试完成后补充。

## 遇到的问题

### 问题1: 配置文件变化

**现象**: 2.x 版本的 `config.h` 在 3.x 中变为 `mbedtls_config.h`

**原因**: 3.x 重构了配置系统

**解决**: 使用新的配置文件名，并提供 `compat-2.x.h` 兼容层

### 问题2: API 变化

**现象**: 部分旧 API 被移除或重命名

**原因**: 3.x 清理了废弃 API

**解决**: 参考 [迁移指南](https://mbed-tls.readthedocs.io/en/latest/kb/ports/migrating-from-mbedtls-2-to-mbedtls-3/)

## 测试结果

详见 [test-report.md](./reports/test-report.md)

| 测试项 | 结果 |
|--------|------|
| 测试套件 | 待补充 |
| 核心加密功能 | 待验证 |
| TLS 协议栈 | 待验证 |
| X.509 证书处理 | 待验证 |

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
# 应显示 aes.h, aria.h, asn1.h 等

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
# 输出: mbedTLS version: 3.6.6
```

### 完整验证脚本

```bash
#!/bin/bash
# verify_mbedtls_3.6.6.sh

PREFIX=$HOME/usr/local

echo "=== 验证 mbedtls 3.6.6 安装 ==="

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

### AES 加密示例（3.x 版本）

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

## 从 2.x 迁移

### 主要 API 变化

1. **配置文件重命名**
   ```c
   // 2.x
   #include "mbedtls/config.h"
   
   // 3.x
   #include "mbedtls/mbedtls_config.h"
   ```

2. **兼容层**
   ```c
   // 在 3.x 中使用 2.x API
   #include "mbedtls/compat-2.x.h"
   ```

3. **移除的 API**
   - 部分 `md_info_t` 相关函数
   - 部分 `ssl_set_xxx` 函数（改为 `ssl_conf_xxx`）

4. **新增功能**
   - TLS 1.3 支持
   - 更严格的错误处理
   - 改进的内存管理

### 迁移步骤

1. 更新头文件包含路径
2. 检查编译警告和错误
3. 使用 `compat-2.x.h` 作为过渡
4. 逐步迁移到新 API

详细迁移指南：https://mbed-tls.readthedocs.io/en/latest/kb/ports/migrating-from-mbedtls-2-to-mbedtls-3/

## 已知限制

### HarmonyOS 平台限制

待测试完成后补充。

### 版本特性

- 此为 3.6 LTS 版本
- 支持 TLS 1.3
- 移除了已废弃的 API
- 提供向后兼容层

## 预编译包

### 下载

预编译包位于：`packaging/mbedtls-3.6.6-ohos-aarch64.tar.gz`

### 安装

```bash
# 解压到目标目录
tar xzf mbedtls-3.6.6-ohos-aarch64.tar.gz -C ~/usr/local

# 运行安装脚本
cd ~/usr/local/mbedtls-3.6.6-ohos-aarch64
sh install-mbedtls-3.6.6.sh

# 验证
pkg-config --libs mbedtls
```

## 经验总结

1. **版本选择**：新项目推荐使用 3.x LTS 版本
2. **迁移策略**：现有项目可使用兼容层逐步迁移
3. **API 文档**：3.x 文档更完善，建议查阅最新文档
4. **测试覆盖**：需要更多测试验证平台兼容性

## 参考资料

- [mbedTLS 3.x 文档](https://mbed-tls.readthedocs.io/en/latest/)
- [迁移指南](https://mbed-tls.readthedocs.io/en/latest/kb/ports/migrating-from-mbedtls-2-to-mbedtls-3/)
- [TLS 1.3 支持](https://mbed-tls.readthedocs.io/en/latest/tutorials/tls13-preview/)
- [HarmonyOS NDK 开发](https://developer.harmonyos.com/)
- [测试报告](./reports/test-report.md)

---

*本页由 openharmony-compile-agent 生成*  
*最后更新: 2026-04-24*