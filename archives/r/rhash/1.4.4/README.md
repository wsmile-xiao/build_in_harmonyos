# rhash 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | RHash |
| 版本 | 1.4.4 |
| 官网 | http://rhash.sourceforge.net/ |
| 源码下载 | https://github.com/rhash/RHash/archive/refs/tags/v1.4.4.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 编译步骤

### 1. 下载源码

```bash
curl -L -o rhash-1.4.4.tar.gz "https://github.com/rhash/RHash/archive/refs/tags/v1.4.4.tar.gz"
tar -xzf rhash-1.4.4.tar.gz
cd RHash-1.4.4
```

### 2. 配置

```bash
./configure --prefix=$HOME/usr/local
```

### 3. 编译

```bash
make -j$(nproc)
```

### 4. 安装

```bash
make install
```

### 5. 测试

```bash
make test test-lib
```

## 功能说明

RHash 支持以下哈希算法：
- CRC32, CRC32C
- MD4, MD5
- SHA1, SHA256, SHA512, SHA3
- AICH, ED2K, DC++ TTH
- BitTorrent BTIH
- Tiger, GOST R 34.11-94, GOST R 34.11-2012
- RIPEMD-160, HAS-160, EDON-R, Whirlpool

## 可选功能

### OpenSSL 优化算法

```bash
# 运行时链接 OpenSSL（推荐）
./configure --enable-openssl-runtime

# 加载时链接 OpenSSL
./configure --enable-openssl --disable-openssl-runtime
```

### 国际化支持

```bash
./configure --enable-gettext
make install install-gmo
```

## 依赖关系

### 被依赖

RHash 可作为校验工具使用，无特定被依赖关系。

## 编译结果

安装后会生成以下文件：

```
$HOME/usr/local/
├── bin/
│   └── rhash          # 主程序
├── lib/
│   ├── librhash.so    # 共享库
│   └── librhash.a     # 静态库（可选）
└── include/
    └── rhash.h        # 头文件
```

## 参考链接

- [RHash 官方网站](http://rhash.sourceforge.net/)
- [RHash GitHub](https://github.com/rhash/RHash)
- [LibRHash 文档](docs/LIBRHASH.md)