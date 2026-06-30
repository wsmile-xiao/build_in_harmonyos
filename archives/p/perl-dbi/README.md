# perl-dbi (Perl DBI - Database Interface)

## 简介

DBI 是 Perl 的数据库接口模块，提供了一套统一的数据库访问 API，支持多种数据库后端（如 MySQL、PostgreSQL、Oracle、SQLite 等）。它是 Perl 数据库编程的标准接口。

### 主要特性

- 统一的数据库访问接口
- 支持多种数据库驱动（DBD::* 模块）
- 支持预处理语句和参数绑定
- 事务支持
- 错误处理机制

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 1.637 | built | 2026-06-10 | 首个适配 OHOS 的版本，支持 PurePerl 模式 |

## OHOS 适配说明

### 编译环境

- **构建系统**: perl_xs (Makefile.PL)
- **编译器**: clang 18.1.8
- **Perl 版本**: 5.42.0
- **依赖**: musl 1.2.5 (头文件)

### 关键适配点

1. **Musl 头文件路径**: Perl XS 模块编译需要 musl 头文件
   ```bash
   CCFLAGS="-I$DEFAULT_PREFIX/include"
   ```

2. **链接参数调整**: 系统缺少 CRT 文件，需要特殊链接参数
   ```bash
   LDDLFLAGS="-nostartfiles -nodefaultlibs"
   ```

3. **SELinux HMDFS 限制**: XS 模块无法在用户目录加载

### 已知问题

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| sys/types.h 找不到 | 系统缺少 C 标准库头文件 | 添加 musl 头文件路径 |
| 链接失败：找不到 crti.o/crtn.o | 系统缺少 CRT 文件 | 添加链接参数 -nostartfiles -nodefaultlibs |
| XS 模块加载失败 | SELinux HMDFS 限制 | 使用 PurePerl 模式或管理员安装 |

## 使用说明

### PurePerl 模式（推荐）

PurePerl 模式使用纯 Perl 实现，无需加载 XS 模块，可以直接在用户目录使用：

```bash
# 设置 PurePerl 模式
export DBI_PUREPERL=2

# 加载 DBI 模块
perl -I$HOME/usr/local/lib/perl5/aarch64-linux -MDBI -e 'print $DBI::VERSION'
# 输出: 1.637
```

### XS 模式

XS 模式使用编译后的共享库文件 (DBI.so)，性能更高但有 SELinux 限制：

```bash
# XS 模式（需要管理员权限安装到系统目录）
perl -MDBI -e 'print $DBI::VERSION'
# 用户目录下会报错: Permission denied
```

### 性能对比

| 模式 | 性能 | 可用性 | 推荐场景 |
|------|------|--------|----------|
| PurePerl | 中等 | ✅ 直接可用 | 开发、测试、一般应用 |
| XS | 高 | ⚠️ 需管理员安装 | 生产环境、高负载场景 |

## 安装指南

### 从源码编译

```bash
# 1. 初始化编译环境
python3 $SKILL_ROOT/scripts/ohc-run.py init-build DBI 1.637

# 2. 生成 Makefile
cd $BUILD_SRC_DIR
perl Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX

# 3. 修改 Makefile（添加 musl 头文件路径）
sed -i 's|^CCFLAGS = |CCFLAGS = -I$DEFAULT_PREFIX/include |' Makefile

# 4. 修改 Makefile（添加链接参数）
sed -i 's|^LDDLFLAGS = |LDDLFLAGS = -nostartfiles -nodefaultlibs |' Makefile

# 5. 编译
make -j1

# 6. 安装
make install
```

### 验证安装

```bash
# PurePerl 模式验证
export DBI_PUREPERL=2
perl -I$HOME/usr/local/lib/perl5/aarch64-linux -MDBI -e 'print $DBI::VERSION'

# 查看 DBI 模块信息
perl -I$HOME/usr/local/lib/perl5/aarch64-linux -MDBI -e 'DBI->installed_versions'
```

## 交付物清单

| 文件 | 大小 | 说明 |
|------|------|------|
| DBI.so | 129KB | XS 模块共享库 |
| DBI.pm | 316KB | PurePerl 模块主文件 |
| DBIXS.h | 26KB | XS 接口头文件 |
| Driver.xst | 23KB | 驱动模板 |
| dbipport.h | 195KB | 移植性头文件 |

## 参考资料

- 官网: https://dbi.perl.org/
- CPAN: https://metacpan.org/pod/DBI
- 源码: http://www.cpan.org/authors/id/T/TI/TIMB/DBI-1.637.tar.gz