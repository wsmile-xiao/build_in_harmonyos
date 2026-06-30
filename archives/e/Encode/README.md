# Encode 3.24 for OpenHarmony

> **编译日期**: 2026-06-10
> **状态**: 🟡 已归档（系统预装版本可用）
> **构建系统**: Makefile.PL (Perl ExtUtils::MakeMaker)

---

## 一、软件简介

Encode 是 Perl 核心模块，提供字符编码转换功能。支持 124 种编码，包括：

- **单字节编码**: ASCII, ISO-8859-* 系列
- **多字节编码**: UTF-8, UTF-16, UTF-32, UTF-7
- **CJK 编码**: GBK, GB2312, Big5, EUC-JP, ShiftJIS, EUC-KR

### 主要功能

```perl
use Encode qw(encode decode);

# UTF-8 编码
my $octets = encode("UTF-8", "测试中文");

# GBK 编码
my $gbk = encode("gbk", "测试中文");

# 解码
my $string = decode("UTF-8", $octets);
```

---

## 二、编译指导

### 构建系统

Perl XS 模块使用 Makefile.PL 构建：

```bash
perl Makefile.PL PREFIX=$DEFAULT_PREFIX
make
make install DESTDIR=$TEST_PREFIX
```

### 鸿蒙平台特殊处理

1. **头文件路径**: 添加 musl 头文件到 CCFLAGS
   ```bash
   -I~/usr/local/include
   ```

2. **链接参数**: 使用 `-nostartfiles -nodefaultlibs`
   ```bash
   -nostartfiles -nodefaultlibs -L~/usr/local/lib -shared
   ```

3. **子模块**: Encode 包含 8 个编码子模块
   - Byte, CN, EBCDIC, JP, KR, Symbol, TW, Unicode

---

## 三、补丁清单

| 补丁文件 | 说明 |
|---------|------|
| 0001-fix-compile-flags-for-ohos.patch | 编译标志修改（文档性补丁） |

---

## 四、已知限制

### SELinux HMDFS 限制

**问题**: HMDFS 上的 XS 模块无法被 Perl 动态加载

```
Can't load '.../Encode.so' for module Encode:
Error loading shared library: Permission denied
```

**原因**: `hishell_hap` SELinux domain 只能加载 `hnp_file:s0` 类型文件

**解决方案**:
- 安装到 `/data/service/hnp` 系统目录
- 使用 binary-sign-tool 签名

### 系统预装版本

OpenHarmony 系统已预装 Encode 3.21：
- 路径: `/data/service/hnp/perl.org/perl_5.42.0/lib/5.42.0/aarch64-linux`
- SELinux type: `hnp_file:s0` ✅
- 功能: 完整可用

---

## 五、功能验证

### 系统版本测试结果（Encode 3.21）

| 测试项 | 状态 | 详情 |
|-------|------|------|
| UTF-8 编码/解码 | ✅ PASS | 字节级验证正确 |
| GBK 编码/解码 | ✅ PASS | 字节级验证正确 |
| GB2312 编码/解码 | ✅ PASS | euc-cn 可用 |
| PerlIO 层支持 | ✅ YES | UTF-8/GBK perlio_ok |
| from_to 转换 | ✅ PASS | 原位转换正常 |
| 支持编码数 | ✅ 124 | 包含完整列表 |
| CJK 编码数 | ✅ 11 | 中日韩编码 |

### 功能完整性评估

**✅ Encode 在鸿蒙平台完全可用**

系统预装的 Encode 3.21 提供完整功能，满足所有编码转换需求。

---

## 六、版本差异

| 版本 | 日期 | 主要变化 |
|------|------|---------|
| 3.21 (系统) | 2024-02-25 | 当前预装版本 |
| 3.24 (编译) | 2026-04-29 | 仅构建改进 |

**结论**: 版本差异无重大功能性变化，系统版本已满足需求。

---

## 七、交付物

### 预编译包

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-encode-3.24-ohos-aarch64.tar.gz | 10MB | 68 个文件，9 个 XS 模块 |

### 安装说明

参见 `3.24/packaging/INSTALL.md`

---

## 八、推荐操作

1. **使用系统预装版本**: Encode 3.21 功能完整 ✅
2. **编译产物保留备用**: archives/e/Encode/3.24 ✅
3. **状态设为 archived**: 无需安装编译版本 ✅

---

**编译协作者**: OpenDesk Agent
**最后更新**: 2026-06-10