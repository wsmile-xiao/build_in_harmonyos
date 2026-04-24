# mbedtls — HarmonyOS/OpenHarmony aarch64 编译指南

## 概述

mbedtls（原名 PolarSSL）是一个开源的 SSL/TLS 库，提供加密、哈希、证书验证等功能。它体积小、易于集成，广泛应用于嵌入式系统和物联网设备。

**项目信息**：
- 官网：https://www.trustedfirmware.org/projects/mbed-tls/
- GitHub：https://github.com/Mbed-TLS/mbedtls
- 许可证：Apache 2.0（版本 2.x）、GPL v2+ 或 Apache 2.0（版本 3.x）

## 软件特性

### 核心组件

1. **mbedcrypto** - 加密原语库
   - 对称加密：AES, Camellia, DES, 3DES, Blowfish, ChaCha20
   - 非对称加密：RSA, ECDSA, ECDH, DH
   - 哈希：MD5, SHA-1, SHA-2, SHA-3
   - MAC：HMAC, CMAC

2. **mbedx509** - X.509 证书解析与生成
   - 证书解析与验证
   - CRL 和证书链验证
   - PKCS#12 解析

3. **mbedtls** - SSL/TLS 协议实现
   - TLS 1.2, TLS 1.3 支持
   - DTLS 1.2 支持
   - 服务器/客户端模式

### HarmonyOS 适配要点

1. **构建系统**：CMake（推荐）
2. **编译器要求**：LLVM Clang
3. **平台检测**：需在 `library/net_sockets.c` 中添加 HarmonyOS 支持
4. **线程安全**：使用 pthread（已适配）
5. **时间函数**：支持 `clock_gettime` 和 `gettimeofday`

## 可用版本

| 版本 | 状态 | 测试通过率 | 补丁数 | 备注 |
|------|------|-----------|--------|------|
| 3.6.6 | ⚠️ partial | - | 0 | LTS 版本，API 有较大变化 |
| 2.28.8 | ⚠️ partial | 89% (96/108) | 0 | 旧版 LTS，API 兼容性好 |

## 快速开始

### 安装预编译包

```bash
# 下载并解压
tar xzf mbedtls-2.28.8-ohos-aarch64.tar.gz -C ~/usr/local

# 运行安装脚本
cd ~/usr/local/mbedtls-2.28.8-ohos-aarch64
sh install-mbedtls-2.28.8.sh

# 验证安装
pkg-config --libs mbedtls
# 输出: -L/path/to/lib -lmbedtls -lmbedx509 -lmbedcrypto
```

### 编译依赖

mbedtls 编译依赖：
- **必需**：CMake >= 3.5, C 编译器
- **可选**：Perl（用于测试）, Python 3（用于脚本）

### 编译命令示例

**版本 2.28.8 (CMake)**:
```bash
tar xzf mbedtls-2.28.8.tar.gz
cd mbedtls-2.28.8

mkdir build && cd build
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DENABLE_PROGRAMS=OFF \
  -DENABLE_TESTING=ON

make -j$(nproc)
make test  # 可选
make install
```

**版本 3.6.6 (CMake)**:
```bash
tar xjf mbedtls-3.6.6.tar.bz2
cd mbedtls-3.6.6

mkdir build && cd build
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DENABLE_PROGRAMS=OFF \
  -DENABLE_TESTING=ON

make -j$(nproc)
make test  # 可选
make install
```

## 版本差异说明

### 2.28.x vs 3.x

1. **API 变化**：
   - 3.x 移除了已废弃的 API
   - 3.x 重构了配置系统（`mbedtls_config.h`）
   - 3.x 更严格的类型检查

2. **配置文件**：
   - 2.x: `config.h`
   - 3.x: `mbedtls_config.h`

3. **向后兼容**：
   - 3.x 提供 `compat-2.x.h` 兼容层
   - 建议新项目使用 3.x

## 已知限制

### HarmonyOS 特定限制

1. **测试套件**：部分测试因平台差异失败（约 11%）
   - 时间相关测试（时区问题）
   - 网络相关测试（socket 路径长度限制）
   - 进程相关测试（`fork` 支持）

2. **功能限制**：
   - 硬件加速：暂不支持（需厂商 SDK）
   - 多线程：基本支持，但性能受限

3. **编译警告**：部分无害警告可忽略

### 版本特定限制

**2.28.8**:
- 通过 96/108 测试（89%）
- 12 个测试失败（已知平台兼容性问题）

**3.6.6**:
- 测试结果待更新
- API 迁移需注意兼容性

## 验证安装

### 快速验证

```bash
# 检查库文件
ls -lh $HOME/usr/local/lib/libmbed*

# 检查头文件
ls -lh $HOME/usr/local/include/mbedtls/

# 简单功能测试
cat > test_mbedtls.c << 'EOF'
#include <stdio.h>
#include <mbedtls/version.h>

int main() {
    printf("mbedTLS version: %s\n", mbedtls_version_get_string());
    return 0;
}
EOF

clang -o test_mbedtls test_mbedtls.c -I$HOME/usr/local/include -L$HOME/usr/local/lib -lmbedcrypto
./test_mbedtls
# 输出: mbedTLS version: 2.28.8 或 3.6.6
```

### 功能验证脚本

```bash
#!/bin/bash
# 验证 mbedtls 安装

PREFIX=$HOME/usr/local

echo "=== 验证 mbedtls 安装 ==="
echo ""

# 检查库文件
echo "1. 检查库文件..."
for lib in libmbedcrypto libmbedtls libmbedx509; do
    if [ -f "$PREFIX/lib/${lib}.a" ]; then
        echo "  ✅ $PREFIX/lib/${lib}.a"
    else
        echo "  ❌ 缺少 $PREFIX/lib/${lib}.a"
    fi
done

# 检查头文件
echo ""
echo "2. 检查头文件..."
if [ -d "$PREFIX/include/mbedtls" ]; then
    header_count=$(ls $PREFIX/include/mbedtls/*.h 2>/dev/null | wc -l)
    echo "  ✅ 找到 $header_count 个头文件"
else
    echo "  ❌ 缺少 mbedtls 头文件目录"
fi

# 检查 pkg-config
echo ""
echo "3. 检查 pkg-config..."
export PKG_CONFIG_PATH=$PREFIX/lib/pkgconfig:$PKG_CONFIG_PATH
if pkg-config --exists mbedtls; then
    echo "  ✅ pkg-config 可以找到 mbedtls"
    echo "  CFLAGS: $(pkg-config --cflags mbedtls)"
    echo "  LIBS: $(pkg-config --libs mbedtls)"
else
    echo "  ⚠️  pkg-config 未配置"
fi

echo ""
echo "=== 验证完成 ==="
```

## 使用示例

### 加密示例

```c
#include <stdio.h>
#include <string.h>
#include "mbedtls/aes.h"

int main() {
    unsigned char key[32] = {0};  // 256-bit key
    unsigned char iv[16] = {0};    // 初始化向量
    unsigned char input[16] = "Hello, HarmonyOS";
    unsigned char output[16];
    
    mbedtls_aes_context aes;
    mbedtls_aes_init(&aes);
    mbedtls_aes_setkey_enc(&aes, key, 256);
    mbedtls_aes_crypt_cbc(&aes, MBEDTLS_AES_ENCRYPT, 16, iv, input, output);
    
    printf("Encrypted: ");
    for (int i = 0; i < 16; i++) {
        printf("%02x", output[i]);
    }
    printf("\n");
    
    mbedtls_aes_free(&aes);
    return 0;
}
```

编译：
```bash
clang -o aes_test aes_test.c -I$HOME/usr/local/include -L$HOME/usr/local/lib -lmbedcrypto
```

### 哈希示例

```c
#include <stdio.h>
#include <string.h>
#include "mbedtls/sha256.h"

int main() {
    unsigned char input[] = "Hello, HarmonyOS";
    unsigned char output[32];
    
    mbedtls_sha256(input, strlen((char*)input), output, 0);
    
    printf("SHA-256: ");
    for (int i = 0; i < 32; i++) {
        printf("%02x", output[i]);
    }
    printf("\n");
    
    return 0;
}
```

## 参考文档

- [mbedTLS 官方文档](https://www.trustedfirmware.org/projects/mbed-tls/)
- [mbedTLS API 参考](https://mbed-tls.readthedocs.io/)
- [迁移指南 2.x 到 3.x](https://mbed-tls.readthedocs.io/en/latest/kb/ports/migrating-from-mbedtls-2-to-mbedtls-3/)
- [HarmonyOS NDK 开发指南](https://developer.harmonyos.com/cn/develop/deveco-studio)

## 贡献与反馈

如遇编译问题或有改进建议，请：
1. 检查 `reports/test-report.md` 了解已知问题
2. 查看 `reports/skill-feedback.md` 提交反馈
3. 参考同目录下的版本级 README 了解具体版本详情

---

*本页由 openharmony-compile-agent 自动生成*
*最后更新: 2026-04-24*