# acme-tiny

## 简介

acme-tiny 是一个极简的 ACME 客户端脚本，用于从 Let's Encrypt 获取和续订 TLS 证书。它非常小巧（不到 200 行代码），易于审计，只需要 Python 和 OpenSSL 作为依赖。

## 特性

- 极简设计：不到 200 行 Python 代码
- 易于审计：源代码简洁清晰
- 低依赖：仅需 Python 和 OpenSSL
- 安全性高：无需 root 权限运行
- 支持 Let's Encrypt ACME 协议

## 安装

### 预编译包安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- acme-tiny 5.0.1
```

### 手动安装

```bash
# 安装依赖
pip3 install acme-tiny

# 或使用源码
python3 setup.py install --prefix=/path/to/install
```

## 使用方法

```bash
# 生成账户密钥
openssl genrsa 4096 > account.key

# 生成 CSR
openssl req -new -sha256 -key domain.key -subj "/CN=example.com" > domain.csr

# 获取证书
acme-tiny --account-key account.key --csr domain.csr --acme-dir /var/www/html/.well-known/acme-challenge/ > signed.crt
```

## 运行时依赖

- Python 3.6+
- OpenSSL 1.1.0+

## 验证安装

```bash
acme-tiny --help
# 或
python3 -m acme_tiny --help
```

## 相关链接

- 上游仓库：https://github.com/diafygi/acme-tiny
- 文档：README.md（源码中）
- 许可证：MIT

## 编译信息

- 版本：5.0.1
- 编译日期：2026-05-22
- 构建系统：setuptools（纯 Python）
- 平台：OpenHarmony aarch64