# perl-rpc-xml

Perl XML-RPC 实现，提供数据类型、客户端和服务器类（RPC::XML）。

## 软件信息

- **官网**: https://metacpan.org/dist/RPC-XML
- **源码**: https://mirrors.tuna.tsinghua.edu.cn/CPAN/authors/id/R/RJ/RJRAY/RPC-XML-0.82.tar.gz
- **许可证**: perl_5 (Artistic License 2.0)
- **分类**: perl-module
- **作者**: Randy J. Ray (RJRAY)

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.82 | published | 2026-06-29 | 纯 Perl 模块，无需特殊适配。核心功能测试 14 项全通过 |

## 运行依赖

- perl 5.42.0

### 必需运行时依赖（尚未编译为 conan 包）

| 依赖 | 最低版本 | 用途 |
|------|---------|------|
| XML::Parser | 2.46 | XML 解析后端 |
| LWP (libwww-perl) | 6.51 | HTTP 客户端 (RPC::XML::Client) |
| HTTP::Daemon | 6.12 | HTTP 服务器 (RPC::XML::Server) |
| HTTP::Message | 6.26 | HTTP 消息处理 |
| Module::Load | 0.36 | 模块加载 |
| Scalar::Util | 1.55 | 标量工具 |

### 可选运行时依赖

| 依赖 | 最低版本 | 用途 |
|------|---------|------|
| XML::LibXML | 2.0206 | 替代 XML 解析后端 |
| DateTime | 1.54 | 日期时间处理 |
| DateTime::Format::ISO8601 | 0.15 | ISO8601 日期解析 |
| Net::Server | - | 独立服务器模式 |
| Compress::Zlib | - | 压缩支持 |

## 编译依赖

无额外依赖（纯 Perl 模块）

## 使用说明

RPC::XML 提供 XML-RPC 协议的完整实现，包括：

- **数据类型**: int, string, boolean, double, array, struct, base64, nil, datetime_iso8601
- **客户端**: RPC::XML::Client — 向 XML-RPC 服务器发送请求
- **服务器**: RPC::XML::Server — 创建 XML-RPC 服务器
- **解析器**: RPC::XML::Parser — XML 解析（支持 XML::Parser 和 XML::LibXML 后端）
- **过程管理**: RPC::XML::Procedure — 管理已注册的 RPC 方法
- **Apache 集成**: Apache::RPC::Server — mod_perl 集成

### 安装

通过 Conan 安装：

```bash
conan install --requires=perl-rpc-xml/0.82@ohpcd/stable
```

模块安装到 `lib/perl5/RPC/XML/` 目录，通过 `PERL5LIB` 环境变量自动加载。

### 示例

```perl
use RPC::XML;

# 创建数据类型
my $int = RPC::XML::int->new(42);
my $str = RPC::XML::string->new("hello");
my $arr = RPC::XML::array->new($int, $str);

# 序列化为 XML
print $int->as_string();   # <int>42</int>
print $arr->as_string();   # <array><data>...</data></array>

# 自动类型推断
my $smart = RPC::XML::smart_encode(3.14);  # RPC::XML::double
print $smart->type();  # double

# nil 支持（需启用）
$RPC::XML::ALLOW_NIL = 1;
my $nil = RPC::XML::nil->new();
print $nil->as_string();  # <nil/>
```

### 注意事项

- 此模块为纯 Perl 实现，不包含 XS 代码，无需 ELF 签名
- 完整的 XML-RPC 客户端/服务器功能需要安装运行时依赖 (XML::Parser, LWP, HTTP::Daemon)
- 核心数据类型创建和序列化功能无需任何运行时依赖
- 模块内部 $VERSION 为 1.61，CPAN 发行版本为 0.82（Perl 模块常见做法）
- `bin/make_method` 工具用于将 .xpl 方法定义文件编译为 Perl 模块
- 无平台特殊限制，可在鸿蒙系统正常使用

---
*OpenHarmony 编译归档 · 2026-06-29*
