# perl-padwalker

PadWalker — play with other peoples' lexical variables (Perl XS module)

## 简介

PadWalker 是一个 Perl XS 模块，提供访问其他作用域中词法变量（lexical variables）的能力。它可以查看和修改调用栈中其他函数的 `my`、`our` 变量，主要用于调试和测试场景。

## 版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 2.5-r5 | built | 2026-07-02 | OHOS 平台适配版 |

## OHOS 平台适配要点

### 编译环境
- **构建系统**: Perl ExtUtils::MakeMaker (Makefile.PL)
- **编译器**: clang 18.1.8
- **Perl**: 5.42.0 (aarch64-linux)
- **源码**: CPAN ROBIN/PadWalker-2.5.tar.gz

### 已解决的问题

1. **系统头文件缺失**: OHOS 缺少标准 C 库头文件路径，通过在 Makefile.PL 的 INC 中添加 musl libc 头文件备份目录解决
2. **CRT 文件缺失**: OHOS 系统缺少 crti.o/crtn.o 等 CRT 文件，通过 `dynamic_lib => { OTHERLDFLAGS => '-nostartfiles -nodefaultlibs -L/system/lib64 -lc' }` 绕过
3. **SELinux HMDFS 限制**: XS 模块 .so 在用户目录（`hmdfs:s0`）无法动态加载，需安装到系统目录（`/data/service/hnp/`，`hnp_file:s0`）

### 运行时安装

XS 模块需要管理员安装到系统目录：

```bash
# 解压 HNP 包到系统 Perl 目录
sudo -u installs unzip perl-padwalker-2.5-r5-ohos-aarch64.hnp \
  -d /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/

# 验证
perl -MPadWalker -e 'print "PadWalker $PadWalker::VERSION\n"'
```

## 功能列表

- `peek_my($level)` — 查看 `my` 变量
- `peek_our($level)` — 查看 `our` 变量
- `peek_sub(\&code)` — 查看子程序的词法变量
- `closed_over(\&code)` — 查看闭包捕获的变量
- `set_closed_over(\&code, \%vars)` — 设置闭包变量
- `var_name($ref)` — 获取变量名

## 许可证

MIT
