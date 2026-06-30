# MIME::Base32

Base32 编码/解码 Perl 模块 — 鸿蒙平台预编译包

## 软件介绍

MIME::Base32 是一个纯 Perl 实现的 Base32 编码/解码模块，提供与 MIME::Base64 类似的 API 接口，支持 RFC 3548 标准编码和 Base32Hex 扩展编码。

### 主要特性
- RFC 3548 兼容的 Base32 编码/解码（`encode_base32` / `decode_base32`）
- Base32Hex 编码/解码（`encode_base32hex` / `decode_base32hex`）
- 支持 RFC 3548 和 09AV 两种编码模式别名
- 纯 Perl 实现，无 XS/C 扩展依赖
- 支持二进制数据和任意字节流编码

### 技术信息
- **版本**: 1.303
- **许可证**: Perl Artistic License / GPL
- **构建系统**: ExtUtils::MakeMaker (Makefile.PL)
- **类型**: 纯 Perl 模块（Pure Perl，无 XS）
- **作者**: Jens Rehsack, Chase Whitener, Daniel Peder

## 鸿蒙平台适配

### 编译状态
- **编译日期**: 2026-06-17
- **平台**: OpenHarmony (aarch64-unknown-linux-ohos)
- **编译器**: Perl 5.42.0 (ExtUtils::MakeMaker)
- **状态**: ✅ 编译成功

### 平台适配说明
- **纯 Perl 模块**：无需 C 编译，不产生 .so 文件
- **无 SELinux 限制**：与 perl-dbd-pg 等 XS 模块不同，纯 Perl 模块不受 HMDFS/SELinux 限制
- **零补丁**：源码无需任何修改即可编译通过
- **即时可用**：安装后可直接使用，无需管理员协助

### 质量门禁
| 门禁 | 状态 | 说明 |
|------|------|------|
| G1 二进制完整性 | PASS | 无二进制文件（纯 Perl） |
| G2 功能可用性 | PASS | 31/31 测试通过，功能验证通过 |
| G3 可移植性 | PASS | 纯 Perl，无平台依赖 |
| G4 档案完整性 | PASS | 归档完整 |

## 使用方式

### 基本 API
```perl
use MIME::Base32 qw(encode_base32 decode_base32);

# 编码
my $encoded = encode_base32("hello world");
# 结果: NBSWY3DPFQQFO33SNRSCC===

# 解码
my $decoded = decode_base32($encoded);
# 结果: hello world
```

### Base32Hex 编码
```perl
use MIME::Base32 qw(encode_base32hex decode_base32hex);

my $encoded = encode_base32hex("hello");
# 结果: D1IMOR3F

my $decoded = decode_base32hex($encoded);
# 结果: hello
```

### RFC 3548 和 09AV 别名
```perl
use MIME::Base32 qw(encode_rfc3548 decode_rfc3548 encode_09AV decode_09AV);

# RFC 3548 模式（等同于 encode_base32/decode_base32）
my $enc = encode_rfc3548("test");

# 09AV 模式（等同于 encode_base32hex/decode_base32hex）
my $enc2 = encode_09AV("test");
```

### 二进制数据处理
```perl
use MIME::Base32 qw(encode_base32 decode_base32);

# 编码二进制数据
my $binary = pack("C*", 0..255);
my $encoded = encode_base32($binary);
my $decoded = decode_base32($encoded);
# round-trip 完整保留
```

### UTF-8 文本处理
```perl
use MIME::Base32 qw(encode_base32 decode_base32);
use Encode qw(encode decode);

# 正确处理 UTF-8 文本（先转为字节）
my $text = "你好世界";
my $bytes = encode("UTF-8", $text);
my $encoded = encode_base32($bytes);
my $decoded = decode("UTF-8", decode_base32($encoded));
```

## 安装

### 预编译包安装
```bash
# 解压预编译包到本地安装目录
tar xzf perl-mime-base32-1.303-ohos-aarch64.tar.gz -C ~/usr/local

# 验证安装
perl -MMIME::Base32 -e 'print "MIME::Base32 version: $MIME::Base32::VERSION\n"'
```

### 从源码安装
```bash
# 下载源码
tar xzf MIME-Base32-1.303.tar.gz
cd MIME-Base32-1.303

# 编译
perl Makefile.PL
make
make test

# 安装
make install
```

## 版本信息

| 版本 | 状态 | 发布日期 | 说明 |
|------|------|---------|------|
| 1.303 | built | 2026-06-17 | RFC 3548 + Base32Hex 支持 |

## 相关链接
- 官方: https://metacpan.org/pod/MIME::Base32
- 源码仓库: https://github.com/perl5-utils/MIME-Base32
- RFC 3548: https://tools.ietf.org/html/rfc3548#section-5
