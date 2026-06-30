# MooseX::Types::URI

## 简介

MooseX::Types::URI 为 Moose 提供 URI 相关的类型约束，包括：

- **Uri** — 通用 URI 类型，接受 URI 对象及其子类、URI::WithBase
- **FileUri** — 文件 URI 类型 (URI::file)
- **DataUri** — 数据 URI 类型 (URI::data)

支持从字符串、HashRef、ScalarRef 自动强制转换为对应的 URI 对象。

## OHOS 适配

- 使用 Module::Build::Tiny (Build.PL) 构建，非标准 Makefile.PL，需手动运行 `perl Build.PL`
- 纯 Perl 模块，无 XS 组件，不涉及 SELinux HMDFS 限制
- 运行时依赖 Moose (含 XS 组件)，需系统 C 头文件支持（musl 1.2.5 已提供）
- Params::Validate 可用 `--pp` 选项纯 Perl 模式安装，避免 XS 编译依赖
- 编译命令: `perl Build.PL --install_base=$DEFAULT_PREFIX && ./Build && ./Build install`

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Perl | 5.42.0 | 运行时 |
| Moose | 2.4000 | 运行时 (含 XS) |
| MooseX::Types | 0.51 | 运行时 |
| URI | 5.21 | 运行时 |
| URI::FromHash | 0.05 | 运行时 |
| Params::Validate | 1.31 | 运行时 (纯 Perl 模式) |
| namespace::autoclean | 0.31 | 运行时 |

## 功能验证

```bash
# 模块加载
perl -MMooseX::Types::URI -e 'print "MooseX::Types::URI version: $MooseX::Types::URI::VERSION\n"'

# 类型约束与强制转换
perl -e '
use MooseX::Types::URI qw(to_Uri);
my $uri = to_Uri("http://openharmony.org");
print "URI: $uri\nScheme: ", $uri->scheme, "\n";
'

# 在 Moose 类中使用
perl -e '
use Moose;
use MooseX::Types::URI qw(Uri);
has url => (is => "rw", isa => Uri, coerce => 1);
my $obj = main->new(url => "https://example.com");
print "URL: ", $obj->url, "\n";
'
```

## 参考

- CPAN: https://metacpan.org/dist/MooseX-Types-URI
- 源码: https://github.com/moose/MooseX-Types-URI
