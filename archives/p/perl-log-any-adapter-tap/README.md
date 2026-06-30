# Log::Any::Adapter::TAP

> Logger suitable for TAP test files

## 简介

Log::Any::Adapter::TAP 是一个 Perl 模块，提供了适用于 TAP (Test Anything Protocol) 测试文件的日志适配器。它可以将 Log::Any 的日志输出转换为 TAP 格式，便于在测试脚本中使用。

这个模块是纯 Perl 实现，无需编译 C 代码，直接安装 .pm 文件即可使用。

## OHOS 适配要点

1. **纯 Perl 模块**：无需编译二进制文件，无需 ELF 签名，无补丁
2. **依赖处理**：依赖 perl-log-any 1.718-r0，必须先安装依赖模块
3. **路径问题**：系统 Perl 的 @INC 不包括用户安装路径，需要使用 PERL5LIB 或 -I 参数指定
4. **测试环境**：测试需要 PERL5LIB 环境变量指定依赖路径才能通过
5. **质量门禁**：所有测试通过 (Files=7, Tests=27, Result: PASS)
6. **上库状态**：✅ 已发布，符合上库要求
7. **预编译包**：已生成，可直接通过 cmd-pkgs 安装脚本安装

## 安装方式

```bash
# 通过 cmd-pkgs 安装脚本安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-log-any-adapter-tap 0.003003-r0
```

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| perl-log-any | 1.718-r0 | Log::Any 核心模块 |
| Try::Tiny | latest | 异常处理模块 |
| Perl | 5.42.0 | Perl 运行环境 |

## 功能验证

```bash
# 验证模块安装
/storage/Users/currentUser/usr/local/bin/perl -I/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0 -MLog::Any::Adapter::TAP -e 'print "Log::Any::Adapter::TAP version: $Log::Any::Adapter::TAP::VERSION\n"'

# 输出应该显示版本号：0.003003
```

## 参考

- [CPAN 页面](http://search.cpan.org/dist/Log-Any-Adapter-TAP/)
- [源码仓库](https://github.com/NERDVANA/Log-Any-Adapter-TAP)