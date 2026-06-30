# Easy-RSA

## 软件简介

Easy-RSA 是一个命令行工具，用于简化 PKI（公钥基础设施）的创建和管理。它是 OpenVPN 项目的一部分，广泛用于生成和管理 X.509 证书、私钥和相关的加密材料，特别适合搭建小型到中型的证书颁发机构（CA）。

## 主要功能

- **PKI 初始化**：创建完整的 PKI 目录结构和配置文件
- **证书颁发机构管理**：生成 CA 证书和私钥
- **证书签发**：签发服务器证书、客户端证书、代码签名证书等
- **证书撤销**：管理证书撤销列表（CRL）
- **密钥管理**：生成 RSA、ECDSA 等类型的密钥对
- **Diffie-Hellman 参数**：生成 DH 参数用于密钥交换
- **多种证书类型支持**：支持服务器、客户端、CA、中间 CA 等多种证书类型

## OHOS 适配

### 适配要点

1. **纯 Shell 实现**：Easy-RSA 是 POSIX shell 脚本工具，无需编译，可直接运行
2. **OpenSSL 依赖**：依赖 OpenSSL 命令行工具，需要预先安装 OpenSSL 1.1.1 或更高版本
3. **路径适配**：安装路径为 `$PREFIX/bin/easyrsa` 和 `$PREFIX/share/easy-rsa/`
4. **版本信息**：通过 sed 替换源码中的版本占位符（`~VER~`、`~DATE~`、`~HOST~`）

### 已知问题

1. **无编译过程**：作为纯脚本工具，传统的 configure/make/make install 流程不适用
2. **版本占位符**：源码中的版本信息需要手动替换（`~VER~` → 实际版本号）
3. **证书路径**：用户需要通过 `source vars.example` 配置 PKI 路径

### 与 Linux 的差异

- **安装方式**：Linux 发行版通常通过包管理器安装，OHOS 需要从源码手动安装
- **路径结构**：遵循 OHOS 标准路径结构（`$PREFIX/bin/` 和 `$PREFIX/share/`）
- **权限管理**：需要确保脚本有可执行权限

## 依赖关系

### 编译依赖

无编译依赖（纯脚本工具）

### 运行依赖

- **OpenSSL**: 1.1.1w 或更高版本（命令行工具和库）
  - 用于证书生成、密钥管理、加密操作
  - 需要在 PATH 中可访问

### 可选依赖

- **git**: 用于某些高级功能（如从 git 仓库读取证书序列号）
- **ssh-keygen**: 用于生成 SSH 密钥对

## 安装方法

### 预编译包安装（推荐）

```bash
# 下载并安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- easy-rsa 3.2.6

# 验证安装
easyrsa --version
```

### 手动安装

```bash
# 1. 下载源码
wget https://github.com/OpenVPN/easy-rsa/archive/refs/tags/v3.2.6.tar.gz
tar xzf v3.2.6.tar.gz
cd easy-rsa-3.2.6/easyrsa3

# 2. 替换版本占位符
VERSION="3.2.6"
DATE=$(date)
HOST=$(hostname)
sed -i "s/~VER~/$VERSION/g" easyrsa
sed -i "s/~DATE~/$DATE/g" easyrsa
sed -i "s/~HOST~/$HOST/g" easyrsa

# 3. 安装到系统路径
PREFIX=$HOME/usr/local
install -m 755 easyrsa $PREFIX/bin/
install -d $PREFIX/share/easy-rsa/x509-types
install -m 644 openssl-easyrsa.cnf $PREFIX/share/easy-rsa/
install -m 644 vars.example $PREFIX/share/easy-rsa/
install -m 644 x509-types/* $PREFIX/share/easy-rsa/x509-types/

# 4. 验证安装
easyrsa --version
```

## 使用示例

```bash
# 初始化 PKI
easyrsa init-pki

# 构建 CA（无密码保护）
easyrsa build-ca nopass

# 生成服务器证书
easyrsa gen-req server.example.com nopass
easyrsa sign-req server server.example.com

# 生成客户端证书
easyrsa gen-req client1.example.com nopass
easyrsa sign-req client client1.example.com

# 生成 DH 参数
easyrsa gen-dh

# 查看证书
easyrsa show-req server.example.com
easyrsa show-cert server.example.com
```

## 参考资料

- **官方仓库**: https://github.com/OpenVPN/easy-rsa
- **官方文档**: https://github.com/OpenVPN/easy-rsa/blob/master/README.md
- **OpenVPN 文档**: https://openvpn.net/community-resources/
- **OpenSSL 文档**: https://www.openssl.org/docs/

## 版本历史

| 版本 | 状态 | 构建日期 | 备注 |
|------|------|---------|------|
| 3.2.6 | built | 2026-05-27 | 当前版本，支持 OpenSSL 1.1.1w |

## 许可证

GPLv2（GNU General Public License version 2）