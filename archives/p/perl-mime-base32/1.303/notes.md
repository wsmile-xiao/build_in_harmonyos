# perl-mime-base32 1.303 适配笔记

## 编译环境
- 构建系统: ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-06-17
- 编译器: Perl 5.42.0
- 平台: OpenHarmony (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

MIME::Base32 是一个**纯 Perl 模块**，编译过程非常简单：

```bash
# 1. 解压源码
tar xzf MIME-Base32-1.303.tar.gz
cd MIME-Base32-1.303

# 2. 生成 Makefile
perl Makefile.PL

# 3. 编译
make

# 4. 测试（31 个用例全部通过）
make test

# 5. 安装到 DESTDIR（staging）
make install DESTDIR=$TEST_PREFIX

# 6. 安装到本地
make install
```

无需任何 configure 参数或编译选项，`perl Makefile.PL` 自动检测 Perl 环境。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| - | 无 | 纯 Perl 模块无需特殊处理 | - |

**与 perl-dbd-pg 的对比**：

| 对比项 | perl-mime-base32 | perl-dbd-pg |
|--------|-----------------|-------------|
| 模块类型 | 纯 Perl（Pure Perl） | XS + Perl（含 C 扩展） |
| 是否需要补丁 | 否（零补丁） | 是（2 个补丁） |
| SELinux 限制 | 无（无 .so 文件） | 有（XS 模块加载受限） |
| 外部依赖 | 无 | libpq, DBI, musl 头文件 |
| make test 结果 | 31/31 PASS | 需特殊处理 |
| 运行时可用性 | 即时可用 | 需管理员安装到系统目录 |

## 源码修改

无修改。源码在 OpenHarmony 平台上无需任何适配即可编译通过。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| Perl | 5.42.0 | 唯一运行时依赖（>= 5.8.1） |

无其他外部依赖。

## 验证结果

```bash
# 模块加载
$ perl -MMIME::Base32 -e 'print "MIME::Base32 version: $MIME::Base32::VERSION\n"'
MIME::Base32 version: 1.303

# make test 结果
$ make test
t/00-base32.t ..... ok
t/01-base32hex.t .. ok
All tests successful.
Files=2, Tests=31, 1 wallclock secs
Result: PASS

# encode/decode round-trip 验证
$ perl -MMIME::Base32 -e '
use MIME::Base32 qw(encode_base32 decode_base32);
my $enc = encode_base32("hello");
my $dec = decode_base32($enc);
print "encode_base32(\"hello\") = $enc\n";
print "decode_base32(\"$enc\") = $dec\n";
'
encode_base32("hello") = NBSWY3DP
decode_base32("NBSWY3DP") = hello
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-mime-base32-1.303-ohos-aarch64.tar.gz | 14,871 bytes | 预编译包（含 Base32.pm 和 .packlist） |

## 注意事项

1. **纯 Perl 模块**：不产生任何二进制文件（.so），因此无需 ELF 签名、无 SELinux 限制
2. **即时可用**：与 perl-dbd-pg 等 XS 模块不同，安装后无需管理员协助即可直接使用
3. **字节操作**：模块操作基于字节而非字符。处理 UTF-8 文本时需先使用 `Encode::encode()` 转为字节
4. **无 padding**：编码输出不含 `=` 填充字符（与 RFC 4648 的标准格式略有差异）
5. **多编码模式**：支持 base32（A-Z2-7）和 base32hex（0-9A-V）两种字母表
