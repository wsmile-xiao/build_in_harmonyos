# certbot

Certbot is EFF's tool to obtain certs from Let's Encrypt and (optionally) auto-enable HTTPS on your server. It can also act as a client for any other CA that uses the ACME protocol.

## 软件信息

- **官网**: https://certbot.eff.org/
- **GitHub**: https://github.com/certbot/certbot
- **PyPI**: https://pypi.org/project/certbot/
- **分类**: network

## 鸿蒙适配要点

### 构建系统

certbot 是纯 Python 包，使用 pip 安装方式。不需要传统的 configure/make 流程。

### 安装方式

```bash
pip3 install --break-system-packages certbot
```

**注意**: 由于 PEP 668，Homebrew 管理的 Python 禁止直接安装包，需要使用 `--break-system-packages` 标志。

### 依赖

certbot 依赖以下 Python 包：

- acme >= 5.1.0
- ConfigArgParse >= 1.5.3
- configobj >= 5.0.6
- cryptography >= 43.0.0
- distro >= 1.0.1
- josepy >= 2.0.0
- parsedatetime >= 2.6
- pyrfc3339
- PyOpenSSL >= 25.0.0
- requests >= 2.25.1

### 特殊说明

1. certbot 是纯 Python 包，不需要 ELF 签名
2. 预编译包包含所有 Python 依赖（约 967 个文件）
3. 用户安装需要 Python 3.10+ 环境

## 已编译版本

| 版本 | 状态 | 日期 | 包大小 |
|------|------|------|--------|
| 5.1.0 | published | 2026-05-19 | 8.1MB |

## 使用示例

```bash
# 安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- certbot 5.1.0

# 验证
certbot --version

# 获取证书（示例）
certbot certonly --webroot -w /var/www/html -d example.com
```

## 相关链接

- [Let's Encrypt 官网](https://letsencrypt.org/)
- [ACME 协议规范](https://datatracker.ietf.org/doc/html/rfc8555)