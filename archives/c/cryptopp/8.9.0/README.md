# crypto++ 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | Crypto++ (cryptopp) |
| 版本 | 8.9.0 |
| 官网 | https://www.cryptopp.com/ |
| 源码下载 | https://github.com/weidai11/cryptopp/archive/refs/tags/CRYPTOPP_8_9_0.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 特性说明

Crypto++ 是 C++ 加密算法库：
- 70+ 加密算法
- 对称加密：AES, DES, Blowfish, ChaCha20
- 公钥加密：RSA, DSA, ECDSA, ECDH
- 哈希：SHA-1, SHA-256, SHA-512, MD5, BLAKE2
- 随机数生成：AES-CTR, ChaCha20

## 编译步骤

### 1. 下载源码

```bash
curl -L -o cryptopp-8.9.0.tar.gz "https://github.com/weidai11/cryptopp/archive/refs/tags/CRYPTOPP_8_9_0.tar.gz"
tar -xzf cryptopp-8.9.0.tar.gz
cd cryptopp-CRYPTOPP_8_9_0
```

### 2. 配置

```bash
cmake -B build \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DBUILD_TESTING=OFF
```

### 3. 编译

```bash
cmake --build build -j$(nproc)
```

### 4. 安装

```bash
DESTDIR=$HOME/tmp/cryptopp cmake --install build
```

### 5. 测试（可选）

```bash
cmake --build build --target test-cryptopp
```

## 使用方法

### AES 加密

```cpp
#include <cryptopp/aes.h>
#include <cryptopp/modes.h>
#include <cryptopp/filters.h>

using namespace CryptoPP;

byte key[AES::DEFAULT_KEYLENGTH];
byte iv[AES::BLOCKSIZE];

// 加密
std::string plaintext = "Hello World";
std::string ciphertext;

CBC_Mode<AES>::Encryption encryptor(key, sizeof(key), iv);
StringSource(plaintext, true,
    new StreamTransformationFilter(encryptor,
        new StringSink(ciphertext)
    )
);

// 解密
std::string decrypted;
CBC_Mode<AES>::Decryption decryptor(key, sizeof(key), iv);
StringSource(ciphertext, true,
    new StreamTransformationFilter(decryptor,
        new StringSink(decrypted)
    )
);
```

### SHA-256 哈希

```cpp
#include <cryptopp/sha.h>

SHA256 hash;
std::string digest;
StringSource("Hello World", true,
    new HashFilter(hash,
        new HexEncoder(new StringSink(digest))
    )
);
```

## 支持的算法

| 类别 | 算法 |
|------|------|
| 对称加密 | AES, DES, 3DES, Blowfish, Twofish, ChaCha20, Salsa20 |
| 公钥加密 | RSA, DSA, ECDSA, ECDH (NIST, Curve25519) |
| 哈希 | SHA-1, SHA-2, SHA-3, MD5, BLAKE2, RIPEMD-160 |
| MAC | HMAC, CMAC, GMAC |
| 随机数 | AES-CTR, ChaCha20, X917 |

## 编译产物

```
$HOME/usr/local/
├── lib/
│   ├── libcryptopp.a    # 静态库
│   └── libcryptopp.so   # 共享库
└── include/
    └── cryptopp/
        ├── aes.h
        ├── sha.h
        ├── rsa.h
        └── ...
```

## 参考链接

- [Crypto++ 官网](https://www.cryptopp.com/)
- [Crypto++ GitHub](https://github.com/weidai11/cryptopp)
- [Crypto++ 文档](https://www.cryptopp.com/docs/)
