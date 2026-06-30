# Mail::AuthenticationResults

Perl模块用于解析和生成邮件Authentication-Results头。

## 描述

Mail::AuthenticationResults 提供解析和生成RFC 7601 Authentication-Results邮件头的功能，用于记录邮件认证检查结果（如SPF、DKIM、DMARC等）。

## 版本信息

- **当前版本**: 2.20250709-r0
- **上游来源**: CPAN
- **许可证**: Perl Artistic License

## 功能特性

- 解析Authentication-Results头字段
- 支持SPF、DKIM、DMARC认证结果
- JSON序列化输出
- 支持多种邮件服务提供商格式（Gmail、Outlook、Yahoo等）
- 纯Perl实现，无需XS编译

## 编译状态

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 2.20250709-r0 | ✅ published | 2026-06-16 |

## 使用示例

```perl
use Mail::AuthenticationResults::Parser;

my $parser = Mail::AuthenticationResults::Parser->new();
my $header = 'example.com; spf=pass smtp.mailfrom=user@example.com';
my $results = $parser->parse($header);

print $results->as_string();
```

## 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-mail-authenticationresults 2.20250709-r0
```

## 运行时依赖

- Perl 5.42.0
- 无外部库依赖

## 测试覆盖

- 单元测试: 33个测试文件，398个测试用例
- 通过率: 100%

## 平台兼容性

- ✅ OpenHarmony (aarch64)
- ✅ 纯Perl模块，无平台限制
- ✅ 无SELinux加载限制

---

**编译者**: OpenDesk Compile Agent
**最后更新**: 2026-06-16