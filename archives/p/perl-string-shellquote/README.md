# perl-string-shellquote

String::ShellQuote - quote strings for passing through the shell.

## 软件信息

- **官网**: https://metacpan.org/dist/String-ShellQuote
- **源码**: https://cpan.metacpan.org/authors/id/R/RO/ROSCH/String-ShellQuote-1.04.tar.gz
- **许可证**: Perl (Same terms as Perl itself)
- **分类**: perl

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.04-r5 | published | 2026-07-06 | 纯 Perl 模块，无需补丁，全部测试通过 |

## 运行依赖

- perl

## 编译依赖

- perl (ExtUtils::MakeMaker)

## 使用说明

String::ShellQuote 提供三个函数用于安全地引用字符串以通过 shell 执行：

- `shell_quote(@list)` - 引用字符串列表，不可引用时 croak
- `shell_quote_best_effort(@list)` - 尽力引用，不 croak
- `shell_comment_quote($string)` - 引用字符串以安全包含在 shell 注释中

还提供 `shell-quote` 命令行工具。

### 安装

Conan 安装：
```bash
conan install --requires=perl-string-shellquote/1.04-r5@ohpcd/stable
```

模块安装路径：`data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/String/ShellQuote.pm`

### 注意事项

- 纯 Perl 模块，无 C/XS 代码，无需处理 CRT 文件缺失或 SELinux 限制
- 与 perl-dbd-pg 等 XS 模块不同，本模块无需任何补丁即可在鸿蒙平台编译运行
- 上游测试套件 33 个测试全部通过

---

*OpenHarmony 编译归档 · 2026-07-03*
