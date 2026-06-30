# Encode 3.24 Perl XS 模块适配笔记

## 编译环境
- 构建系统: Makefile.PL (Perl ExtUtils::MakeMaker)
- 编译日期: 2026-06-10
- 编译器: clang 18.1.8
- Perl 版本: 5.42.0
- 状态: archived

## 编译步骤

### 1. 生成 Makefile
```bash
perl Makefile.PL \
  PREFIX=$DEFAULT_PREFIX \
  LIB=$DEFAULT_PREFIX/lib/perl5/site_perl \
  INSTALLSITELIB=$DEFAULT_PREFIX/lib/perl5/site_perl \
  INSTALLSITEARCH=$DEFAULT_PREFIX/lib/perl5/site_perl/aarch64-linux
```

### 2. 修改编译标志
```bash
# 添加 musl 头文件路径
sed -i 's/^CCFLAGS = -D_GNU_SOURCE/CCFLAGS = -I\/storage\/Users\/currentUser\/usr\/local\/include -D_GNU_SOURCE/' Makefile

# 修改链接器标志
sed -i 's|^LDDLFLAGS = -shared|LDDLFLAGS = -nostartfiles -nodefaultlibs -L/storage/Users/currentUser/usr/local/lib -shared|' Makefile
```

### 3. 编译
```bash
TMPDIR=/storage/Users/currentUser/tmp make -j1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sys/types.h 找不到 | Perl 默认编译标志不包含 musl 头文件路径 | 添加 `-I~/usr/local/include` 到 CCFLAGS |
| 2 | CRT 文件找不到 | 链接器在默认位置找不到 CRT 文件 | 使用 `-nostartfiles -nodefaultlibs` |
| 3 | XS 模块无法加载 | SELinux HMDFS 限制 | 系统已预装 Encode 3.21，功能完整 |

## 功能测试结果

### 系统预装 Encode 3.21 测试

| 测试项 | 状态 |
|-------|------|
| UTF-8 编码/解码 | ✅ PASS |
| GBK 编码/解码 | ✅ PASS |
| GB2312 编码/解码 | ✅ PASS |
| PerlIO 层支持 | ✅ YES |
| 支持编码数 | 124 种 |

## 最终状态

- **编译状态**: archived
- **功能可用性**: 系统预装版本完全可用
- **推荐操作**: 无需安装编译版本