# testssl 编译指南

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | testssl.sh |
| 版本 | 3.2.3 |
| 官网 | https://testssl.sh/ |
| 源码下载 | https://github.com/drwetter/testssl.sh/archive/refs/tags/v3.2.3.tar.gz |

## 编译环境

- 操作系统: HarmonyOS / OpenHarmony
- 编译器: 无需编译（Shell 脚本）
- 目标架构: aarch64

## 特性说明

testssl.sh 是 TLS/SSL 配置检查工具：
- Shell 脚本，无需编译
- 检测 TLS 协议版本
- 检查加密套件
- 验证证书链
- 检测已知漏洞

## 安装步骤

### 1. 下载源码

```bash
curl -L -o testssl-3.2.3.tar.gz "https://github.com/drwetter/testssl.sh/archive/refs/tags/v3.2.3.tar.gz"
tar -xzf testssl-3.2.3.tar.gz
cd testssl.sh-3.2.3
```

### 2. 安装

```bash
mkdir -p $HOME/usr/local/bin
mkdir -p $HOME/usr/local/share/testssl

cp testssl.sh $HOME/usr/local/bin/
cp -r etc/ $HOME/usr/local/share/testssl/
chmod +x $HOME/usr/local/bin/testssl.sh
```

## 使用方法

### 基本用法

```bash
# 检查单个主机
testssl.sh example.com

# 检查特定端口
testssl.sh example.com:8443

# 批量检查
testssl.sh --file hosts.txt

# 只检查协议
testssl.sh --protocols example.com

# 只检查加密套件
testssl.sh --ciphers example.com
```

### 输出格式

```bash
# JSON 输出
testssl.sh --json example.com

# HTML 输出
testssl.sh --html example.com

# CSV 输出
testssl.sh --csv example.com
```

## 检查项目

| 类别 | 检查内容 |
|------|---------|
| 协议 | SSLv2, SSLv3, TLS 1.0-1.3 |
| 加密套件 | 强度、顺序、Forward secrecy |
| 证书 | 验证、链、有效期、SAN |
| 漏洞 | Heartbleed, POODLE, BEAST, CRIME |
| 扩展 | OCSP stapling, HSTS, ALPN |

## 依赖

- OpenSSL 或 aws-lc（二进制）
- bash 4.0+

## 编译产物

```
$HOME/usr/local/
├── bin/
│   └── testssl.sh     # 主脚本
└── share/
    └── testssl/
        └── etc/       # 配置文件
```

## 参考链接

- [testssl.sh 官网](https://testssl.sh/)
- [testssl.sh GitHub](https://github.com/drwetter/testssl.sh)