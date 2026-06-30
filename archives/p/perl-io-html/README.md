# IO-HTML

## 简介

IO::HTML - Open an HTML file with automatic charset detection

IO::HTML 提供了一个简单的接口来打开 HTML 文件并自动检测字符编码。

## 主要功能

- 自动检测 HTML 文件的字符编码
- 遵循 HTML5 规范的编码检测算法
- 纯 Perl 实现，无需 XS 编译
- 支持 HTTP 头部和 meta 标签中的编码声明

## 版本

- **1.004** (2026-06-11): 编译成功，测试通过

## 依赖

### 运行时依赖
- Perl >= 5.008
- Carp
- Encode >= 2.10
- Exporter >= 5.57

### 构建依赖
- ExtUtils::MakeMaker

## 编译状态

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.004 | built | 2026-06-11 | 纯 Perl 模块，编译成功 |

## 使用方法

```perl
use IO::HTML;

# 打开 HTML 文件并自动检测编码
my $fh = html_file('index.html');

# 读取内容
my $content = do { local $/; <$fh> };
close $fh;
```

## 许可证

Perl License (GPLv1+ or Artistic License)

## 作者

Christopher J. Madsen <perl@cjmweb.net>

## 更多信息

- CPAN: https://metacpan.org/pod/IO::HTML
- 源码: https://github.com/cjm/IO-HTML