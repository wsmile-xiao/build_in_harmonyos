# ssh-copy-id

## 软件简介
ssh-copy-id 是一个 Shell 脚本工具，用于将本地 SSH 公钥安装到远程服务器的授权密钥文件中。它是 OpenSSH 项目的一部分，简化了 SSH 密钥认证的设置过程。

## 主要功能
- 自动将本地公钥（默认 ~/.ssh/id_rsa.pub）添加到远程服务器的 ~/.ssh/authorized_keys
- 支持多种 SSH 密钥类型（RSA、DSA、ECDSA、Ed25519 等）
- 提供干运行模式（dry-run）预览将要添加的密钥
- 支持 SFTP 方式安装密钥（当远程不支持 SSH 时）

## 技术特点
- 纯 Shell 脚本实现，无需编译
- 兼容 POSIX sh 和 bash
- 依赖系统已安装的 ssh 和 ssh-keygen 命令

## 版本说明
- 版本号跟随 OpenSSH 主版本
- 当前版本：9.9p1（对应 OpenSSH 9.9p1）

## 许可证
BSD 2-Clause License（与 OpenSSH 相同）

## 安装要求
- OpenHarmony aarch64 平台
- 已安装 OpenSSH 客户端（ssh, ssh-keygen）
- POSIX 兼容的 shell 环境

## 使用示例
```bash
# 将默认公钥复制到远程服务器
ssh-copy-id user@remote-host

# 指定公钥文件
ssh-copy-id -i ~/.ssh/my_key.pub user@remote-host

# 干运行模式（预览）
ssh-copy-id -n user@remote-host
```

## 编译状态
- 类型：Shell 脚本（无需编译）
- 状态：packaged
- 平台：OpenHarmony aarch64
