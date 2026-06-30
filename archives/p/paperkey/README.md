# paperkey — OpenPGP 密钥纸质备份工具

## 简介

paperkey 是一个用于将 OpenPGP（GnuPG/PGP）密钥的"秘密部分"提取并打印到纸上的工具。
纸质备份可作为数字备份的终极兜底方案——优质纸张和墨水的保存期可达数百年，远超现代数字存储介质。

核心思路：OpenPGP 密钥的元数据和冗余使其体积远大于仅含"秘密位"的部分。
paperkey 只提取并打印这些秘密位，恢复时结合公开密钥重建完整密钥。

例如：一个 DSA+Elgamal 密钥（1281字节）的秘密部分仅 149 字节。

## 基本信息

| 项目 | 值 |
|------|-----|
| 版本 | 1.6 |
| 作者 | David Shaw (dshaw@jabberwocky.com) |
| 许可证 | GPLv2+ |
| 项目主页 | https://www.jabberwocky.com/software/paperkey/ |
| 源码下载 | https://github.com/dmshaw/paperkey/releases/download/v1.6/paperkey-1.6.tar.gz |
| 构建系统 | autotools |

## 编译状态

| 版本 | 状态 | 补丁 | 编译日期 |
|------|------|------|----------|
| 1.6 | ✅ published | 1 (umask E011) | 2026-06-17 |

## 使用示例

提取密钥秘密部分：
```bash
paperkey --secret-key my-secret-key.gpg --output to-be-printed.txt
```

从秘密数据恢复密钥（需配合公开密钥）：
```bash
paperkey --pubring my-public-key.gpg --secrets my-key-text-file.txt --output my-secret-key.gpg
```

## 支持的密钥类型

- RSA
- DSA + ElGamal
- ECC (Curve25519 等)
- EdDSA

## 鸿蒙平台编译说明

需要应用 1 个补丁：`0001-configure-remove-umask-077.patch`
（修复 HMDFS 文件系统 umask 077 权限问题，详见知识图谱 E011）
