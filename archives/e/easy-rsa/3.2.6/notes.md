# easy-rsa 3.2.6 适配笔记

## 编译环境
- 构建系统: shell（纯脚本工具，无需编译）
- 编译日期: 2026-05-27
- 编译器: 无（shell 脚本）
- 状态: published

## 编译步骤

Easy-RSA 是一个纯 POSIX shell 脚本工具，用于管理 PKI（公钥基础设施）。无需传统编译过程。

1. **下载源码**: 从 GitHub 下载 v3.2.6 tarball
2. **解压源码**: 解压到工作目录
3. **手动安装**: 复制 easyrsa3/ 目录中的文件到目标位置
   - `easyrsa` 脚本 → `$DEFAULT_PREFIX/bin/easyrsa`
   - `openssl-easyrsa.cnf` → `$DEFAULT_PREFIX/share/easy-rsa/`
   - `vars.example` → `$DEFAULT_PREFIX/share/easy-rsa/`
   - `x509-types/` → `$DEFAULT_PREFIX/share/easy-rsa/x509-types/`
4. **版本替换**: 使用 sed 替换版本占位符（~VER~, ~DATE~, ~HOST~）
5. **功能测试**: 运行 `--version` 和 `init-pki` 验证基本功能
6. **创建预编译包**: 打包安装文件为 tar.gz

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无法自动检测下载 URL | Easy-RSA 不在 registry 中 | 手动提供 GitHub URL |
| 2 | 版本信息显示占位符 | 未运行 build-dist.sh | 使用 sed 替换占位符 |
| 3 | tar 打包路径过长警告 | ustar 格式限制 | 使用 Python 创建 tar.gz |

## 源码修改

无补丁文件。所有修改通过 sed 命令完成：
- 替换 `~VER~` → `3.2.6`
- 替换 `~DATE~` → 当前日期
- 替换 `~HOST~` → 主机名

## 依赖版本

- OpenSSL: 1.1.1w（运行时依赖）

## 验证结果

```bash
$ easyrsa --version
EasyRSA Version Information
Version:     3.2.6
Generated:   Wed May 27 17:20:09 CST 2026
SSL Lib:     OpenSSL 1.1.1w  11 Sep 2023

$ easyrsa init-pki
'init-pki' complete; you may now create a CA or requests.
```

## 交付物

| 文件 | 大小 | SHA256 |
|------|------|--------|
| easy-rsa-3.2.6-ohos-aarch64.tar.gz | 61499 bytes | d23b04efa69284bc460fc2c98fd7f0effadcc0353d90260b46e0e319fdb68598 |

包含文件：
- `usr/local/bin/easyrsa` (197980 bytes) - 主脚本
- `usr/local/share/easy-rsa/` - 配置文件目录
- `usr/local/share/doc/easy-rsa/` - 文档目录

## 注意事项

1. Easy-RSA 是 shell 裚本，不需要 ELF 签名（但依赖的 openssl 需要）
2. 需要确保 OpenSSL 已安装并在 PATH 中
3. 预编译包解压后，easyrsa 脚本可直接执行
4. 建议用户通过 `source vars.example` 配置环境变量
---

**编译结束**: 2026-05-27 20:02
**最终状态**: built
