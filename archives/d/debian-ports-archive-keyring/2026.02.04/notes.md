# debian-ports-archive-keyring 2026.02.04 — 适配笔记

## 概述
Debian-native 源包（无独立 upstream，无 C/C++ 代码）。debian-ports 归档用本包携带的
OpenPGP 密钥对 Release 文件签名。真实产物 = 数据/信任（keyring）文件，非程序。

## 真实身份
- 官方上游: https://salsa.debian.org/aurel32/debian-ports-archive-keyring（tag debian/2026.02.04）
- 源: Debian pool `debian-ports-archive-keyring_2026.02.04.tar.xz`（sha 见 conandata，实测）
- 维护者: Aurelien Jarno；许可: GPL-2+（包元数据/文件；密钥为 Debian 归档签名证书）

## 内容
源 `active-keys/*.key`（2 个活跃：2026、2027）与 `removed-keys/*.key`（19 个历史：2007-2025）。
Debian 二进制包安装:
- /etc/apt/trusted.gpg.d/debian-ports-archive-{2026,2027}.asc （= 源 .key 逐字节一致）
- /usr/share/keyrings/debian-ports-archive-keyring.pgp（活跃，二进制，3560B）
- /usr/share/keyrings/debian-ports-archive-keyring-removed.pgp（历史，二进制，30518B）

## 适配方案（data/keyring package）
- Conan `package_type="unknown"` + `settings` 四项显式（CI L0 门禁），无 settings 语义。
- `build()`: 用纯 python 复现 debian/rules 的 `gpg --import`（armor 解码 + 按年份序拼接
  完整公钥包），并对官方 .deb 内 4 文件 sha256 硬门禁——**内容与上游一致，漂移即 BUILD_ERROR**。
  不需要 gpg/网络。
- `package()`: 装到 `share/keyrings/`，`resdirs=["share"]`，无 bin → 无 commands.json（R38 库/数据包）。
- `test_package`: 纯数据验证（无 gpg 可用）：文件存在、sha256==官方 .deb、ASCII-armor/OpenPGP
  packet 解析、v4 fingerprint（活跃 2 把已知；removed 19 主钥）。本地 `conan create` 已 PASS。

## 上游测试
无测试套件（无 debian/tests、无 check 目标）→ upstream 0/0。上述为 Harmony 特有
data/keyring 真实性验证，非 upstream test（如实归类）。

## 事实核验记录（2026-09-09）
- 版本 2026.02.04 存在（snapshot 与主 pool；注意有 trixie 变体 2026.02.04~deb13u1，勿混）。
- 官方 .deb 内 4 文件 sha256 已实测；重建 .pgp 与官方逐字节一致。
- 活跃指纹（gpg 与纯 python v4 双复核）:
  5FFACC4B97F15BF3636639EBC6894E6BB25B9C99 (2026)
  16AD6A4476B489F604203E42C5934E9A2B1BE090 (2027)
- 说明: 活跃 2026 钥于 2027-02-01 过期，长期使用需随 Debian 升版（2027 key 在包内）。
