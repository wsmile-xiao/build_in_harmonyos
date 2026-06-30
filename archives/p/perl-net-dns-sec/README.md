# perl-net-dns-sec

**Net::DNS::SEC** — DNSSEC extensions to Net::DNS (Perl XS module with libcrypto).

提供 DNSSEC 签名验证功能，包括 DSA、RSA、ECDSA、EdDSA 签名算法支持，依赖 OpenSSL libcrypto 进行加密操作。

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.26-r1 | built | 2026-06-25 | 编译成功，功能测试不通过（XS 加密功能不可用） |

## 功能

Net::DNS::SEC 提供以下功能：

- **DNSSEC 签名验证** — 支持 DSA/RSA/ECDSA/EdDSA 算法 ❌ **鸿蒙不可用**（依赖 XS libcrypto）
- **密钥管理** — Private/PrivateKey 读取与管理 ✅ 可用（纯 Perl）
- **摘要计算** — 支持 SHA-1/SHA-256/SHA-384/GOST 摘要 ❌ **鸿蒙不可用**（依赖 XS libcrypto）
- **Keyset** — DNSKEY 集合处理 ✅ 可用（纯 Perl）
- **XS 加速** — C 扩展 (SEC.so) 提供高性能加密操作 ❌ **鸿蒙不可用**（SELinux 阻止 dlopen）
- **工具函数** — algorithm()/digtype() 编号↔助记符转换 ✅ 可用（纯 Perl）
- **RR 处理** — DS/DNSKEY 记录创建与解析 ✅ 可用 / RRSIG ❌ 不可用

## 使用说明

> ⚠️ **鸿蒙平台限制**: 以下签名/验证/摘要操作在鸿蒙上**不可用**，因为 XS .so 无法加载。
> 仅模块加载、工具函数、DS/DNSKEY 记录处理、Keyset/Private 文件处理可用。

```perl
use Net::DNS::SEC;

# 工具函数 — 鸿蒙可用
my $alg = algorithm(8);        # "RSASHA256"
my $dt = digtype(2);           # "SHA-256"

# 以下操作在鸿蒙上不可用（需要 XS libcrypto）
use Net::DNS::SEC::Private;
my $keyfile = 'Kexample.com.+008+12345.private';
my $private = Net::DNS::SEC::Private->new($keyfile);  # Private 模块可加载
# $sig = $key->sign($rrset);   # ❌ RSA/ECDSA/EdDSA sign 不可用
# $key->verify($sig, $rrset);  # ❌ verify 不可用
```

## 平台兼容性

**功能测试日期**: 2026-06-26

### ❌ 核心加密功能不可用

- **XS .so 加载**: OpenHarmony SELinux 阻止所有用户可写路径的 dlopen()，SEC.so 无法加载
- **加密子模块**: RSA/ECDSA/DSA/EdDSA/Digest 在 `BEGIN` 块中 `die`，无纯 Perl 加密回退
- **RRSIG 记录**: "type RRSIG not implemented"（依赖 XS 注册）

### ✅ 可用功能（纯 Perl）

- 模块加载 (`use Net::DNS::SEC`)
- 工具函数: `algorithm()` / `digtype()` 编号↔助记符转换
- DS / DNSKEY 记录创建与解析
- Keyset 文件处理 (`Net::DNS::SEC::Keyset`)
- 私钥文件读取 (`Net::DNS::SEC::Private`)

### 依赖

- OpenSSL 1.1.1w (libcrypto) — 已安装但 dlopen 被阻止
- Net::DNS 1.55+
- Perl 5.42.0

### 结论

软件在鸿蒙平台上**不可正常使用**。编译链接成功，但运行时 XS .so 无法加载导致
所有 DNSSEC 加密操作（签名、验证、摘要）不可用。仅可作为依赖占位（模块加载层面兼容）。
