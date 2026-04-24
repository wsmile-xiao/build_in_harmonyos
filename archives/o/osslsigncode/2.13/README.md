# osslsigncode 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | osslsigncode |
| 版本 | 2.13 |
| 官网 | https://github.com/mtrojnar/osslsigncode |
| 源码下载 | https://github.com/mtrojnar/osslsigncode/archive/refs/tags/2.13.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: clang (OHOS SDK)
- 目标架构: aarch64

## 特性说明

osslsigncode 是 Windows 代码签名工具：
- Authenticode 签名
- PE 文件签名（.exe, .dll）
- MSI 文件签名
- CAB 文件签名
- 时间戳支持

## 编译步骤

### 1. 下载源码

```bash
curl -L -o osslsigncode-2.13.tar.gz "https://github.com/mtrojnar/osslsigncode/archive/refs/tags/2.13.tar.gz"
tar -xzf osslsigncode-2.13.tar.gz
cd osslsigncode-2.13
```

### 2. 配置

```bash
cmake -B build \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release
```

### 3. 编译

```bash
cmake --build build -j$(nproc)
```

### 4. 安装

```bash
DESTDIR=$HOME/tmp/osslsigncode cmake --install build
```

## 使用方法

### 签名 PE 文件

```bash
# 使用证书签名
osslsigncode sign -certs cert.pem -key key.pem \
    -t http://timestamp.digicert.com \
    -in unsigned.exe -out signed.exe

# 使用 PKCS#12 证书
osslsigncode sign -pkcs12 cert.p12 -pass password \
    -t http://timestamp.digicert.com \
    -in unsigned.exe -out signed.exe
```

### 验证签名

```bash
osslsigncode verify -in signed.exe
```

### 时间戳

```bash
osslsigncode timestamp -t http://timestamp.digicert.com -in signed.exe
```

## 参数说明

| 参数 | 说明 |
|------|------|
| -certs | 证书链 PEM 文件 |
| -key | 私钥 PEM 文件 |
| -pkcs12 | PKCS#12 证书文件 |
| -pass | PKCS#12 密码 |
| -t | 时间戳服务器 URL |
| -in | 输入文件 |
| -out | 输出文件 |

## 已知限制

- 需要 cURL 支持（HTTP 时间戳）
- 当前版本缺少 cURL，时间戳功能受限

## 编译产物

```
$HOME/usr/local/
├── bin/
│   └── osslsigncode   # 命令行工具
└── share/
    └── man/man1/       # 手册页
```

## 参考链接

- [osslsigncode GitHub](https://github.com/mtrojnar/osslsigncode)
- [Authenticode 规范](https://docs.microsoft.com/en-us/windows-hardware/drivers/install/authenticode)
