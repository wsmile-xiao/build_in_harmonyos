# perl-mime-base64

MIME::Base64 — Base64 编码/解码和 Quoted-Printable 编码的 Perl XS 加速模块。

## 版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 3.16 | published | 2026-06-18 | XS 编译成功，系统预装版本可用 |

## 概述

MIME::Base64 提供 Base64 和 Base64URL 编码/解码功能，以及 MIME::QuotedPrint 的 Quoted-Printable 编解码。模块使用 XS (C 语言) 实现以获得高性能。

## 鸿蒙平台使用说明

### 系统预装版本（推荐）

HarmonyOS 系统预装的 Perl 5.42.0 已包含 MIME::Base64 3.16_01，**功能完整可用**，无需额外安装。

```perl
use MIME::Base64;
print encode_base64("Hello");  # SGVsbG8=
```

### 影子加载问题

如果用户在 `~/usr/local/lib/` 中编译安装了 MIME::Base64，用户目录的 .so 会影子加载系统版本，但由于 HMDFS SELinux 限制无法 dlopen。

**解决方法**: 移除用户目录中的 .so 和 .pm 文件：
```bash
rm -f ~/usr/local/lib/site_perl/5.42.0/aarch64-linux/auto/MIME/Base64/Base64.so
rm -f ~/usr/local/lib/site_perl/5.42.0/aarch64-linux/MIME/Base64.pm
rm -f ~/usr/local/lib/site_perl/5.42.0/aarch64-linux/MIME/QuotedPrint.pm
```

### 自定义安装（需要管理员权限）

使用 HNP 包安装到系统目录：
```bash
sudo -u installs unzip perl-mime-base64-3.16.hnp \
  -d /data/service/hnp/perl.org/perl_5.42.0/
```

## API

```perl
use MIME::Base64 qw(encode_base64 decode_base64 encode_base64url decode_base64url);
use MIME::QuotedPrint qw(encode_qp decode_qp);

$encoded = encode_base64('Hello');        # SGVsbG8=\n
$decoded = decode_base64('SGVsbG8=\n');   # Hello
$url_enc = encode_base64url("\xFB\xFF");  # -_8
$qp_enc  = encode_qp('café');             # caf=C3=A9=\n
```

## 平台限制

- HMDFS 文件系统不允许 `hishell_hap` 域 dlopen `hmdfs:s0` 类型的 .so
- 影响所有安装在用户目录 (`/storage/Users/currentUser/`) 的 Perl XS 模块
- 解决方案：使用系统预装版本，或通过 HNP 包安装到 `/data/service/hnp/`
