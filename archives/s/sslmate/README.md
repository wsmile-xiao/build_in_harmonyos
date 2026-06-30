# sslmate

sslmate 是一个通过 SSLMate 服务购买和管理 SSL 证书的命令行工具。

- **官网**: https://sslmate.com
- **许可证**: MIT 风格（详见源码 COPYING 文件）
- **语言**: Perl（需要 Perl 5.10+）
- **构建系统**: 纯 Makefile（无 configure 脚本）

## 编译说明

- 构建系统：纯 Makefile，使用 `PREFIX` 变量控制安装路径
- 无 configure 脚本，不需要 autotools
- 构建：`make PREFIX=$DEFAULT_PREFIX`
- 安装：`make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX`
- 运行时依赖：Perl 模块 Term::ReadKey（需手动从 CPAN 安装）

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 1.10.0 | ✅ 已发布 | 2026-06-17 | 需安装 Term::ReadKey 2.38 Perl 模块 |

## 验证方式

```bash
sslmate version        # 输出: SSLMate 1.10.0
sslmate                # 输出用法说明
```

注意：sslmate 使用子命令 `version`，不是 `--version` 参数。
