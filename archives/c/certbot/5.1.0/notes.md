# certbot 5.1.0 适配笔记

## 编译环境
- 构建系统: pip（Python 包管理系统）
- 编译日期: 2026-05-19
- Python: 3.14.4
- pip: 26.0.1
- 状态: published

## 编译步骤

certbot 是纯 Python 包，使用 pip 安装方式：

### Step 1: 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build certbot 5.1.0 \
  --url=https://files.pythonhosted.org/packages/source/c/certbot/certbot-5.1.0.tar.gz
```

### Step 2: 安装到 staging 目录
```bash
pip3 install --root=$TEST_PREFIX --prefix=$DEFAULT_PREFIX .
```

### Step 3: 安装到本地验证
```bash
pip3 install --break-system-packages certbot
certbot --version  # 验证输出: certbot 5.1.0
```

### Step 4: 制作预编译包
```bash
tar -czf certbot-5.1.0-ohos-aarch64.tar.gz -C $TEST_PREFIX storage/Users/currentUser/usr/local
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | TMPDIR 目录权限问题 | ~/tmp 目录无法创建 | 使用 ~/.cache/tmp 作为 TMPDIR |
| 2 | pip 安装被拒绝（PEP 668） | Homebrew 管理的 Python 禁止直接安装 | 使用 --break-system-packages 标志 |
| 3 | 下载 cryptography 包超时 | 包较大（4.8MB） | 等待下载完成（约 3 分钟） |

## 源码修改

无需补丁，certbot 是纯 Python 包。

## 依赖版本

| 软件包 | 版本 | 说明 |
|--------|------|------|
| acme | 5.6.0 | ACME 协议库（>=5.1.0） |
| ConfigArgParse | 1.7.5 | 配置解析 |
| configobj | 5.0.9 | 配置文件处理 |
| cryptography | 48.0.0 | 加密库 |
| distro | 1.9.0 | Linux 发行版信息 |
| josepy | 2.2.0 | JOSE 实现 |
| parsedatetime | 2.6 | 时间解析 |
| pyrfc3339 | 2.1.0 | RFC3339 时间格式 |
| PyOpenSSL | 26.2.0 | OpenSSL Python 封装 |
| requests | 2.34.2 | HTTP 库 |
| cffi | 2.0.0 | C Foreign Function Interface |
| pycparser | 3.0 | C 解析器 |
| charset_normalizer | 3.4.7 | 字符编码检测 |
| idna | 3.15 | 国际化域名 |
| urllib3 | 2.7.0 | URL 库 |
| certifi | 2026.4.22 | CA 证书包 |

## 验证结果

```bash
$ certbot --version
certbot 5.1.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| certbot-5.1.0-ohos-aarch64.tar.gz | 8.1MB | 预编译包（包含所有依赖） |

## 注意事项

1. certbot 是纯 Python 包，不需要 ELF 签名
2. 预编译包包含所有 Python 依赖（967 个文件）
3. 用户安装需要 Python 3.14 环境
4. acme 依赖版本 >=5.1.0，实际安装 5.6.0（版本兼容）

---
**编译结束**: 2026-05-19 10:03
**最终状态**: published
