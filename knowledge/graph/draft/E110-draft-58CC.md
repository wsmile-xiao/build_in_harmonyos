# E106: SSL 证书验证失败

> **结构化数据**: [graph/draft/E106-ssl-certificate-fail.kv](../graph/draft/E106-ssl-certificate-fail.kv) | **原则**: P-NETWORK-001
> **严重度**: 🟡 warning | **分类**: network | **自动修复**: ✅ use-alternative-source

---

## 错误特征

```
SSL certificate problem: unable to get local issuer certificate
certificate verify failed
curl: (60) SSL certificate problem
wget: ERROR: cannot verify certificate
```

## 根因

鸿蒙系统可能缺少 CA 证书包，或证书过期，导致 HTTPS 下载失败。

## 解决方案

### 方案 1：使用不安全下载（临时）

```bash
# curl
curl -k -L -o source.tar.gz https://example.com/source.tar.gz

# wget
wget --no-check-certificate https://example.com/source.tar.gz
```

⚠️ **警告**：不验证证书存在安全风险，仅用于测试环境。

### 方案 2：使用 git clone 替代下载

```bash
# GitHub 源码
git clone --depth 1 https://github.com/user/project.git

# 避免证书问题
git clone --depth 1 git@github.com:user/project.git  # SSH 协议
```

### 方案 3：使用镜像站点

```bash
# 使用国内镜像
curl -L -o source.tar.gz https://mirror.example.com/source.tar.gz
```

### 方案 4：安装 CA 证书包

```bash
# 从 cmd-pkgs 安装 ca-certificates
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- ca-certificates 20250419
```

## 涉及软件

- ruby-build（下载 Ruby 源码）
- 所有需要 HTTPS 下载的软件

## 相关模式

- [E002](E002.md) — 临时目录不可写（可能影响下载目录）
- [E105](E105.md) — Shell 脚本工具安装（可能组合出现）

---
*doc/E106.md · knowledge graph v2 · 2026-05-19*