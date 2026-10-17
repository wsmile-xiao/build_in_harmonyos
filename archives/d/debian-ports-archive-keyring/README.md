# debian-ports-archive-keyring

Debian 的 debian-ports 归档签名密钥环（keyring）数据包。用于校验 debian-ports.org 镜像上
Release 文件的 OpenPGP 签名。本仓库将其作为 **data/keyring package** 适配到
Conan/OpenHarmony：无编译，产物为纯密钥数据，验证与部署均不依赖 gpg/apt/网络。

## 上游
- 维护：Aurelien Jarno（Debian）
- 源码：https://salsa.debian.org/aurel32/debian-ports-archive-keyring
- Debian 源包：`debian-ports-archive-keyring_2026.02.04.tar.xz`（Debian-native, Format 3.0）

## 内容
- 活跃归档密钥 ×2（2026、2027，RSA-4096）
- 历史移除密钥 ×19（2007-2025）
- 打包产物：`share/keyrings/{debian-ports-archive-2026.asc, ...-2027.asc,
  debian-ports-archive-keyring.pgp, debian-ports-archive-keyring-removed.pgp}`

## 适配要点
- `build()` 用纯 python 复现上游 `gpg --import` 组装，并与官方 .deb 内文件 **sha256 硬门禁**。
- `test_package` 做 Harmony 特有真实性验证（文件 sha、OpenPGP 结构、key 数/fingerprint）。
- 上游无测试套件 → upstream 0/0，如实申报。

## 部署/升级注意
活跃 2026 钥 2027-02-01 过期；随 Debian 版本滚动升级即更新密钥集（Conan 版本号 = Debian
源包版本 2026.02.04）。
