# Email::Address::XS

Parse and format RFC 5322 email addresses and groups - high performance XS implementation.

## 功能概述

- **邮件地址解析**: 支持复杂 RFC 5322 地址格式（显示名、注释、组）
- **邮件地址格式化**: RFC 5322 标准输出
- **地址验证**: 结构有效性检查
- **高性能**: XS (C) 实现，比纯 Perl 版本快 10 倍以上

## OHOS 适配要点

### 编译参数

Perl XS 模块使用 Makefile.PL 构建，需要显式指定编译参数：

```bash
perl Makefile.PL PREFIX=$DEFAULT_PREFIX \
  CCFLAGS="-D_GNU_SOURCE ... -I$DEFAULT_PREFIX/include" \
  LDDLFLAGS="-shared -nostdlib -B$DEFAULT_PREFIX/lib -lc"
```

关键参数说明：
- `CCFLAGS`: 包含系统头文件路径（Perl 编译时 clang 版本可能不匹配）
- `LDDLFLAGS`: `-nostdlib` 绕过 musl libunwind.a 缺失问题
- `-B$DEFAULT_PREFIX/lib`: ld.lld 链接器搜索路径

### SELinux HMDFS 限制

**问题**: XS.so 从用户目录 (`~/usr/local/lib`) 加载失败
```
Can't load '.../XS.so': Permission denied
```

**原因**:
- 用户目录 SELinux type: `hmdfs:s0`
- hishell_hap domain 只能加载 `hnp_file:s0` 类型文件

**解决方案**: 安装预编译包到系统目录
```bash
tar xzf Email-Address-XS-1.05-ohos-aarch64.tar.gz \
  -C /data/service/hnp/perl.org/perl_5.42.0/
```

## 依赖关系

### 编译依赖
- perl/5.42.0
- Carp (Perl 核心模块)
- XSLoader (Perl 核心模块)

### 运行依赖
- Perl 5.42.0+
- 无额外库依赖

## 与 Email::Address 的区别

| 特性 | Email::Address::XS | Email::Address |
|------|---------------------|-----------------|
| 实现 | XS (C) | PurePerl |
| 性能 | 高（10倍+） | 低 |
| PurePerl fallback | ❌ 无 | ✅ 本身就是 |
| OHOS 可用 | ✅ 需安装到系统目录 | ✅ 直接可用 |

## 模块使用示例

```perl
use Email::Address::XS;

# 创建地址
my $addr = Email::Address::XS->new(
    phrase => 'Winston Smith',
    user   => 'winston.smith',
    host   => 'recdep.minitrue',
    comment => 'Records Department'
);
print $addr->address();  # winston.smith@recdep.minitrue

# 解析地址
my @addresses = Email::Address::XS->parse(
    '"Winston Smith" <winston@minitrue>, Julia <julia@ficdep>'
);

# 验证地址
my $addr = Email::Address::XS->parse_bare_address('user@example.com');
print $addr->is_valid() ? "valid" : "invalid";
```

## 安装方式

### 方式 1: 使用预编译包（推荐）

```bash
# 安装到系统目录
tar xzf Email-Address-XS-1.05-ohos-aarch64.tar.gz \
  -C /data/service/hnp/perl.org/perl_5.42.0/
```

### 方式 2: 使用 cmd-pkgs 公共脚本

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh \
  | sh -s -- Email-Address-XS 1.05
```

### 验证安装

```bash
perl -MEmail::Address::XS -e 'print $Email::Address::XS::VERSION, "\n"'
# 预期输出: 1.05
```

## 参考资料

- [CPAN - Email::Address::XS](https://metacpan.org/pod/Email::Address::XS)
- [RFC 5322 - Internet Message Format](https://tools.ietf.org/html/rfc5322)
- [源码仓库](https://github.com/pali/Email-Address-XS)