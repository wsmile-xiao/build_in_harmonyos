# Encode::JIS2K

Perl XS 扩展模块，提供 JIS X 0212 (JIS2000) 和 JIS X 0213 (JIS2004) 字符集编码支持。

## 功能概述

- 支持 JIS X 0212 字符集编码
- 支持 JIS X 0213 字符集编码
- 提供 iso-2022-jp-3 编码别名
- 与 Perl Encode 模块集成

## OHOS 适配

### 功能测试结论（2026-06-11）

| 测试项 | 状态 | 备注 |
|-------|------|------|
| 编译产物完整性 | ✅ PASS | ELF 结构正确，已签名 |
| Encode::JP 系统模块 | ✅ PASS | iso-2022-jp 编码正常 |
| Encode::JIS2K 本地加载 | ❌ FAIL | HMDFS SELinux 限制 |
| HNP 包制作 | ✅ PASS | 供管理员安装 |

**结论**: XS 模块需管理员安装到系统目录才能正常使用。

### 关键问题

1. **sys/types.h 找不到**：Perl CORE 头文件依赖系统头文件，鸿蒙缺少 `/usr/include`，需添加 Ohos SDK sysroot include 路径
2. **crti.o/crtbeginS.o 找不到**：链接器默认路径不包含 Ohos SDK，需添加 `-nostartfiles` 跳过 crt 文件
3. **libunwind.a 找不到**：Perl XS 扩展链接需要 LLVM 运行时库，需添加 LLVM lib 路径
4. **ELF 签名**：共享库需要签名才能在鸿蒙系统执行
5. **HMDFS SELinux 限制**：签名后的 .so 文件在 HMDFS 目录无法加载，需安装到 `/data/service/hnp`

### 编译要点

```bash
# Makefile.PL 配置
perl Makefile.PL PREFIX=~/usr/local

# 修改 Makefile（自动或手动）
# CCFLAGS += -I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include
# CCFLAGS += -I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/aarch64-linux-ohos
# LDDLFLAGS += -nostartfiles
# LDDLFLAGS += -L/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos

# 编译
make

# 签名（必须）
/data/service/hnp/bin/binary-sign-tool sign -inFile blib/arch/auto/Encode/JIS2K/JIS2K.so -outFile JIS2K.so.signed -selfSign 1

# 安装
make install DESTDIR=~/tmp/test-install-perl-encode-jis2k-0.05-r2
```

## 依赖关系

### 编译依赖
- Perl 5.42.0
- Encode 模块 >= 1.41
- enc2xs 工具

### 运行依赖
- Perl 5.42.0
- Encode 模块

## 管理员安装指南

Encode::JIS2K 是纯 XS 模块（无 PurePerl fallback），必须安装到系统目录：

```bash
# 1. 解压 HNP 包到系统目录（需要 installs 用户权限）
sudo -u installs tar -xzf perl-encode-jis2k.hnp \
    -C /data/service/hnp/perl.org/perl_5.42.0/lib/5.42.0/aarch64-linux/

# 2. 验证安装
perl -MEncode::JIS2K -e 'print "Encode::JIS2K loaded successfully\n";'

# 3. 测试编码功能
perl -e 'use Encode::JIS2K; use Encode qw(encode decode);
    my $str = encode("iso-2022-jp-3", "テスト");
    print "Encoded: ", length($str), " bytes\n";'
```

**安装位置**: `/data/service/hnp/perl.org/perl_5.42.0/lib/5.42.0/aarch64-linux/`

**SELinux 要求**: 文件必须是 `hnp_file:s0` 类型才能被 hishell_hap domain 加载。

## 参考资料

- CPAN: https://metacpan.org/pod/Encode::JIS2K
- 源码: https://cpan.metacpan.org/authors/id/D/DA/DANKOGAI/Encode-JIS2K-0.05.tar.gz