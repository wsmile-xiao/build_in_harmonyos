# Email-Address-XS 1.05 适配笔记

## 编译环境
- 构建系统: perl_xs (Makefile.PL + ExtUtils::MakeMaker)
- 编译日期: 2026-06-10
- 编译器: clang 18.1.8
- 状态: built（编译成功，需管理员部署）

## 编译步骤

1. **下载源码**: 从 CPAN (PALI 作者目录)下载
   ```

### 验证安装

```bash
perl -MEmail::Address::XS -e 'print $Email::Address::XS::VERSION, "\n"'
# 预期输出: 1.05

# 功能测试
perl -MEmail::Address::XS -e 'my $addr = Email::Address::XS->new("Test", "test@example.com"); print $addr->address, "\n"'
# 预期输出: test@example.com
```bash
   wget https://www.cpan.org/authors/id/P/PA/PALI/Email-Address-XS-1.05.tar.gz
   tar xzf Email-Address-XS-1.05.tar.gz
   cd Email-Address-XS-1.05
   ```

2. **生成 Makefile**:
   ```bash
   perl Makefile.PL PREFIX=$DEFAULT_PREFIX \
     CCFLAGS="-D_GNU_SOURCE -fno-strict-aliasing -pipe -fstack-protector-strong -D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64 -I$DEFAULT_PREFIX/include" \
     LDFLAGS="-L$DEFAULT_PREFIX/lib" \
     LDDLFLAGS="-shared -nostdlib -B$DEFAULT_PREFIX/lib -L$DEFAULT_PREFIX/lib -lc"
   ```

3. **编译**:
   ```bash
   make
   ```

4. **安装**:
   ```bash
   make install
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败下载源码 | Savannah站点证书问题 | 从CPAN直接下载 (PALI作者目录) |
| 2 | errno.h/sys/types.h找不到 | Perl编译时使用的clang版本(21)与当前版本(18)不匹配 | 添加CCFLAGS="-I$DEFAULT_PREFIX/include" |
| 3 | crti.o/crtbeginS.o等找不到 | ld.lld默认搜索路径不含本地lib目录 | 添加-B$DEFAULT_PREFIX/lib参数 |
| 4 | libunwind.a找不到 | ld.lld默认链接libunwind，系统无此库 | 使用-nostdlib跳过默认库 |
| 5 | XS.so加载Permission denied | SELinux HMDFS限制，hishell_hap只能加载hnp_file类型 | 创建HNP包，管理员安装到系统目录 |

## 关键编译参数

**CCFLAGS**:
```
-D_GNU_SOURCE -fno-strict-aliasing -pipe -fstack-protector-strong -D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64 -I$DEFAULT_PREFIX/include
```

**LDDLFLAGS**:
```
-shared -nostdlib -B$DEFAULT_PREFIX/lib -L$DEFAULT_PREFIX/lib -lc
```

## 功能测试结果

### 编译产物验证 ✅
- XS.so: 42KB, ELF64 AArch64, 已签名
- XS.pm: 21KB, Perl 模块完整
- 导出符号: boot_Email__Address__XS, compose_address, message_address_parse 等

### 运行时测试 ❌ (SELinux HMDFS限制)
```
perl -MEmail::Address::XS -e 'print "OK\n"'
# 结果: Permission denied (hmdfs:s0 类型无法加载)
```

**对比验证**:
| 文件位置 | SELinux type | 加载结果 |
|---------|-------------|----------|
| `/data/service/hnp/...` (系统) | `hnp_file:s0` | ✅ 可加载 |
| `~/usr/local/lib/...` (HMDFS) | `hmdfs:s0` | ❌ Permission denied |

### HNP 包创建 ✅
- 文件: `Email-Address-XS-1.05-ohos-aarch64.hnp` (24KB)
- 内容: XS.pm (21KB), XS.so (42KB)
- 签名: 已使用 binary-sign-tool 签名

## 模块功能

**主要函数**:
- `parse_email_addresses` - 解析多个邮件地址
- `format_email_addresses` - 格式化邮件地址列表
- `compose_address` - 组合邮件地址

**主要方法**:
- `new` - 创建邮件地址对象
- `parse` - 解析单个地址
- `phrase/user/host/address/comment` - 地址组件操作
- `is_valid` - 验证地址有效性

## 源码修改

无补丁，纯参数配置。

## 依赖版本

- perl/5.42.0 (静态链接)
- Carp (Perl 核心模块)
- XSLoader (Perl 核心模块)

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| Email-Address-XS-1.05-ohos-aarch64.tar.gz | 74KB | 标准预编译包 |
| Email-Address-XS-1.05-ohos-aarch64.hnp | 24KB | HNP 安装包 |
| XS.so | 42KB | Perl XS 模块（已签名） |
| XS.pm | 21KB | Perl 模块文件 |

## 安装指南

### 方式 1: 使用 tar.gz 预编译包

```bash
# 解压到 Perl 系统目录（推荐）
tar xzf Email-Address-XS-1.05-ohos-aarch64.tar.gz -C /data/service/hnp/perl.org/perl_5.42.0/

# 或者使用 cmd-pkgs 公共安装脚本
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- Email-Address-XS 1.05
```

### 方式 2: 使用 HNP 包

```bash
# 解压 HNP 包到系统目录
sudo -u installs unzip Email-Address-XS-1.05-ohos-aarch64.hnp -d /data/service/hnp/perl.org/perl_5.42.0/
```

### 验证安装

```bash
perl -MEmail::Address::XS -e 'print $Email::Address::XS::VERSION, "\n"'
# 预期输出: 1.05

# 功能测试
perl -MEmail::Address::XS -e 'my $addr = Email::Address::XS->new("Test", "test@example.com"); print $addr->address, "\n"'
# 预期输出: test@example.com
```

## 注意事项

1. **SELinux HMDFS限制**: XS模块必须安装到系统目录才能加载
2. **无PurePerl fallback**: 本模块依赖XS实现，无法用纯Perl替代
3. **签名必需**: 系统目录的XS.so需要在系统环境下重新签名获得正确的SELinux type
4. **参考 perl-dbd-pg**: 已验证相同方案可行

---
**编译结束**: 2026-06-10 20:24
**测试结束**: 2026-06-10 20:45
**打包结束**: 2026-06-10 20:54
**最终状态**: built（编译成功，预编译包已创建：tar.gz(74KB) + hnp(24KB)，需管理员部署）
---

**编译结束**: 2026-08-06 08:56
**最终状态**: built
