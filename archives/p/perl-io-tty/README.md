# IO::Tty

IO::Tty 是 Perl 的 PTY/TTY 操作模块，提供伪终端接口功能。

## 功能概述

- **IO::Tty** - TTY（终端）操作接口
- **IO::Pty** - PTY（伪终端主端）创建和管理
- **IO::Tty::Constant** - 终端相关常量定义

主要用途：
- 终端模拟器实现
- 进程间通信（通过伪终端）
- 自动化测试脚本（expect 模式）

## OHOS 适配

### 编译要点

1. **链接参数**: 所有 Perl XS 模块需要 `-nostartfiles -nodefaultlibs`
2. **配置检测**: Makefile.PL 检测 PTY/TTY 函数时因 CRT 缺失会失败，需硬编码检测结果
3. **环境变量**: 必须设置 CPATH 和 LIBRARY_PATH 指向 musl 头文件和库

### 运行时限制

**SELinux HMDFS 限制**: XS 模块（.so 文件）在用户目录无法加载，需要管理员安装到系统目录：
```
/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/IO/Tty/
```

### 可用功能

- 纯 Perl 模块（IO::Tty::Constant）可在用户目录直接使用
- XS 模块需管理员安装后可用

## 依赖关系

### 编译依赖
- perl >= 5.42.0
- musl >= 1.2.5（提供标准 C 库头文件）
- clang >= 18.1.8

### 运行依赖
- perl >= 5.42.0

## 参考资料

- [CPAN: IO::Tty](https://metacpan.org/pod/IO::Tty)
- [GitHub: TODDR/IO-Tty](https://github.com/toddr/IO-Tty)