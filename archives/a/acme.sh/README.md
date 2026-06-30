# acme.sh

**ACME Protocol Client Written Purely in Shell Script**

## 简介

acme.sh 是一个完全用 Shell 脚本实现的 ACME 协议客户端，用于从 Let's Encrypt、ZeroSSL 等 CA 获取 SSL/TLS 证书。

## 特性

- 🐚 纯 Shell 脚本实现，无需编译
- 🔑 支持 ECDSA 证书
- 🌐 支持 SAN 和通配符证书
- 📦 无依赖，独立运行
- 🔄 自动证书签发、续期、安装

## 编译状态

| 版本 | 状态 | 构建系统 | 日期 |
|------|------|----------|------|
| 3.1.3 | built | none (Shell) | 2026-06-04 |

## 安装

```bash
# 从预编译包安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- acme.sh 3.1.3

# 验证安装
acme.sh --version
```

## 使用示例

```bash
# 签发证书
acme.sh --issue -d example.com -w /var/www/html

# 安装证书到 Nginx
acme.sh --install-cert -d example.com \
  --key-file       /etc/nginx/ssl/example.com.key  \
  --fullchain-file /etc/nginx/ssl/example.com.cer  \
  --reloadcmd      "nginx -s reload"
```

## 官方资源

- **主页**: https://github.com/acmesh-official/acme.sh
- **Wiki**: https://github.com/acmesh-official/acme.sh/wiki

## 许可证

GPL-3.0

---

*由 OpenDesk 编译智能体维护*