# acme-tiny-pyc

## 简介

acme-tiny-pyc 是 [acme-tiny](https://github.com/diafygi/acme-tiny)（一个极简的
Let's Encrypt ACME 客户端）的**预编译 Python bytecode 子包**。Alpine 打包生态中
`acme-tiny` 主包安装 `acme_tiny.py`，`acme-tiny-pyc` 子包额外生成
`__pycache__/acme_tiny.cpython-*.pyc` 供 python3 直接加载，在保持脚本可审计的
同时提升冷启动性能。

本归档按路径 A 将 acme-tiny-pyc 5.0.3 作为**独立 Conan 包**归档，源码来源为
acme-tiny 5.0.3 的 PyPI sdist（同一上游项目 diafygi/acme-tiny）。

## 特性

- 极简设计：单文件 Python 脚本（约 200 行），易于审计
- 预编译 bytecode：包内含 `__pycache__/acme_tiny.cpython-*.pyc`（独立包同时
  保留运行所需模块文件 `acme_tiny.py`，自包含可运行）
- 低依赖：仅需 python3 与 openssl 命令行工具
- 支持 Let's Encrypt ACME v2 协议

## 安装

### 预编译包安装（推荐：Conan）

```bash
conan install --requires=acme-tiny-pyc/5.0.3 --build=missing
```

### cmd-pkgs 脚本安装（可选，两步方式）

> ⚠️ 安全提示：请勿将远程脚本直接管道给 shell 执行（`curl ... | sh`）。
> 请先下载并审阅脚本内容、核对校验和，确认无误后再手动执行。

```bash
# 第一步：下载安装脚本，审阅内容并校验
curl -fsSL -o install.sh https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh
less install.sh          # 审阅脚本内容，确认行为符合预期
sha256sum install.sh     # 核对发布方提供的校验和（如有）

# 第二步：确认无误后，再手动执行
sh install.sh -- acme-tiny-pyc 5.0.3
```

### 手动安装（源码）

```bash
python3 -m pip install acme_tiny-5.0.3.tar.gz   # PEP 517 / setuptools
# 或直接使用包内模块：python3 -c "import acme_tiny"
```

## 使用方法

```bash
# 生成账户密钥
openssl genrsa 4096 > account.key

# 生成 CSR
openssl req -new -sha256 -key domain.key -subj "/CN=example.com" > domain.csr

# 签发证书（需要 openssl 命令）
acme-tiny --account-key ./account.key --csr ./domain.csr \
  --acme-dir /var/www/.well-known/acme-challenge/ > signed_chain.crt
```

## 依赖

- python3（运行时解释器）
- openssl（运行时命令依赖：`openssl dgst -sha256 -sign` / `openssl rsa`）

## 许可证

MIT（Copyright Daniel Roesler, diafygi@gmail.com，见上游 LICENSE）
