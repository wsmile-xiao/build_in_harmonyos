# LWP-MediaTypes

LWP::MediaTypes - guess media type for a file or a URL

## 版本历史

| 版本 | 状态 | 日期 |
|------|------|------|
| 6.04 | built | 2026-06-15 |

## 描述

LWP::MediaTypes 是一个 Perl 模块，用于根据文件名或 URL 推断媒体类型（MIME类型）。它是 libwww-perl (LWP) 系列的一部分。

## 依赖

- Perl >= 5.006002
- Carp
- Exporter
- File::Basename
- Scalar::Util

## 鸿蒙适配说明

- 构建系统: Perl ExtUtils::MakeMaker
- 无需编译二进制文件（纯 Perl 模块）
- 安装路径: `$PREFIX/lib/site_perl/5.42.0/LWP/MediaTypes.pm`

## 使用示例

```perl
use LWP::MediaTypes;

# 根据 URL 推断媒体类型
my $type = media_type("http://example.com/image.jpg");
# 返回: image/jpeg

# 根据文件名推断媒体类型
my $type = media_type("/path/to/document.pdf");
# 返回: application/pdf
```

## 相关模块

- LWP::UserAgent - HTTP 客户端
- HTTP::Message - HTTP 消息处理
- URI - URL 处理