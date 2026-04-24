# BearSSL 0.6 — OpenHarmony 编译记录

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件 | bearssl |
| 版本 | 0.6 |
| 状态 | ⚠️ partial（功能完整可用） |
| 构建系统 | custom Makefile（无标准 autotools） |
| 目标平台 | ohos-aarch64 |
| 编译日期 | 2026-04-23 ~ 2026-04-24 |
| 源码 URL | https://www.bearssl.org/git/BearSSL |

## 编译指导

### 构建系统特点

BearSSL 0.6 使用自定义 Makefile 系统，**无标准的 configure 脚本和 make install 目标**：
- 配置文件位于 `conf/` 目录
- 使用 `make CONF=<config>` 选择配置
- 需要手动创建 OpenHarmony 配置文件
- 安装步骤需要手动处理

### 详细编译步骤

```bash
# 1. 解压源码
tar xzf bearssl-0.6.tar.gz
cd bearssl-0.6

# 2. 创建 OpenHarmony 配置（conf/Ohos.mk）
# 需要在 conf/ 目录创建 Ohos.mk 配置文件
# 使用 clang 和 llvm-ar 工具链

# 3. 编译
make CONF=Ohos

# 4. 手动安装（静态库模式）
mkdir -p $HOME/usr/local/lib
mkdir -p $HOME/usr/local/include/bearssl
cp build/Ohos/libbearssl.a $HOME/usr/local/lib/
cp inc/*.h $HOME/usr/local/include/bearssl/

# 5. 安装命令行工具（可选）
cp build/Ohos/brssl $HOME/usr/local/bin/
```

### 配置文件要点（conf/Ohos.mk）

```makefile
CC = clang
AR = llvm-ar
LD = clang
CFLAGS = -Os -fPIC
LDFLAGS = 
```

## 补丁清单

**patches/ 目录状态**：无补丁文件

BearSSL 0.6 源码原生支持 OpenHarmony 平台，仅需添加配置文件即可编译。

## 已知限制

| 限制项 | 说明 | 影响 |
|--------|------|------|
| 无标准安装流程 | 无 `make install` 目标 | 需手动复制文件 |
| DLL API 不稳定 | 官方不推荐动态库模式 | 仅提供静态库 |
| 平台特定优化缺失 | AES_x86ni、AES_pwr4 不可用 | 性能影响小，功能完整 |
| 静态链接为主 | 适合嵌入式场景 | 动态链接需自行处理 |

## 功能验证

### 测试结果汇总

| 测试项 | 状态 | 详情 |
|--------|------|------|
| testcrypto all | ✅ 通过 | 所有加密算法测试通过 |
| testx509 | ✅ 通过 | 57 个证书验证测试通过 |
| brssl impl | ✅ 可用 | 命令行工具正常运行 |

### 详细测试报告

#### testcrypto all

| 类别 | 测试项 | 结果 |
|------|--------|------|
| 哈希算法 | MD5, SHA-1, SHA-224/256/384/512 | ✅ 全部通过 |
| MAC | HMAC | ✅ 通过 |
| KDF | HKDF | ✅ 通过 |
| DRBG | HMAC_DRBG, AESCTR_DRBG | ✅ 通过 |
| 对称加密 | AES (big/small/ct/ct64), DES (tab/ct) | ✅ 通过 |
| 流密码 | ChaCha20 | ✅ 通过 |
| 认证加密 | Poly1305 | ✅ 通过 |
| 公钥算法 | RSA (i15/i31/i32/i62), EC (prime/p256/c25519) | ✅ 通过 |
| 签名 | ECDSA | ✅ 通过 |

**注意**：AES_x86ni 和 AES_pwr4 在 ARM 平台上不可用（预期行为）

#### testx509

测试 X.509 证书验证功能，包括：
- 基础证书验证
- CA 信任链验证
- 名称约束验证
- 通配符匹配
- 哈希算法验证
- 日期有效性验证
- EC 签名验证
- 证书策略验证

**结果**：57 个测试全部通过 ✅

#### brssl 工具验证

```bash
$ brssl impl
BR_64: 1
BR_CLANG: 1
BR_INT128: 1
BR_USE_UNIX_TIME: 1
```

## 预编译包

### 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bearssl-0.6-ohos-aarch64.tar.gz | 1.5 MB | 预编译静态库 + 头文件 |
| bearssl-0.6-ohos-aarch64-debug.tar.gz | - | 调试符号文件 |
| install-bearssl-0.6.sh | - | 安装脚本 |

### 安装方法

```bash
# 解压到用户目录
tar xzf bearssl-0.6-ohos-aarch64.tar.gz -C ~/usr/local

# 或使用安装脚本
sh install-bearssl-0.6.sh
```

### 包内容

```
bearssl-0.6-ohos-aarch64/
├── bin/
│   └── brssl              # 命令行 SSL 工具
├── lib/
│   └── libbearssl.a       # 静态库
└── include/
    └── bearssl/           # 头文件
        ├── bearssl.h
        ├── bearssl_aead.h
        ├── bearssl_block.h
        ├── bearssl_ec.h
        ├── bearssl_hash.h
        ├── bearssl_hmac.h
        ├── bearssl_kdf.h
        ├── bearssl_pem.h
        ├── bearssl_prf.h
        ├── bearssl_rand.h
        ├── bearssl_rsa.h
        ├── bearssl_ssl.h
        └── bearssl_x509.h
```

## 使用示例

### 编译链接

```c
// test.c
#include <bearssl.h>

int main() {
    br_sha256_context ctx;
    br_sha256_init(&ctx);
    // ...
    return 0;
}
```

```bash
# 编译
clang -I$HOME/usr/local/include test.c -L$HOME/usr/local/lib -lbearssl -o test
```

## 相关报告

- [测试报告](reports/test-report.md) - 详细的测试结果
- [质量报告](reports/quality-report.md) - 质量门禁验证结果
- [编译进度](PROGRESS.md) - 完整的编译过程记录
