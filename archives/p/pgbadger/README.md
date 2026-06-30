# pgbadger

## 简介
pgBadger 是一个 PostgreSQL 日志分析器，能快速分析大量日志文件并生成详细的 HTML 报告，包含查询统计、错误分析、连接趋势等性能指标。

## OHOS 适配
- 纯 Perl 脚本程序，使用 Perl MakeMaker 构建（perl Makefile.PL → make → make install）
- 鸿蒙 date 命令不支持 `--date=@timestamp` 语法，需手动运行 pod2man 生成 man page
- 需设置 `PERL5LIB=$HOME/usr/local/lib/perl5` 环境变量
- 测试套件部分失败（1/4 文件通过）均为平台限制引起，不影响核心功能
  - `/tmp` 只读 (E002 HMDFS 限制)
  - 缺少 JSON::XS 模块
  - toybox stat 不支持某些选项

## 依赖
- Perl >= 5.10.0
- 可选：JSON::XS（加速 JSON 解析）

## 功能验证
```bash
# 版本检查
pgbadger --version
# 输出: pgBadger version 13.2

# 生成 HTML 报告
pgbadger /path/to/postgresql.log -o report.html

# 生成文本报告
pgbadger /path/to/postgresql.log -o report.txt

# 显示帮助
pgbadger --help
```

## 参考
- GitHub: https://github.com/darold/pgbadger
- 文档: https://pgbadger.darold.net/