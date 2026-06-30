# JSON::Path

JSON::Path 是一个 Perl 模块，用于使用 JSONPath 表达式搜索嵌套的 hashref/arrayref 结构。JSONPath 是一种类似 XPath 的查询语言，专门用于 JSON 数据结构。

## 功能概述

- **JSONPath 查询**：使用标准 JSONPath 表达式查询 JSON 数据
- **灵活访问**：支持数组索引、通配符、切片、负索引等
- **值提取**：提取匹配路径的所有值或单个值
- **路径映射**：对匹配的值执行自定义操作
- **JSON 集成**：与 JSON::MaybeXS 无缝集成

主要函数：
- `jpath($data, $expression)` - 查询并返回所有匹配值
- `jpath1($data, $expression)` - 查询并返回单个值（lvalue）
- `jpath_map { ... } $data, $expression` - 对匹配值执行映射操作

## OHOS 适配

### 特点

✅ **纯 Perl 模块**：无 XS 组件，无需特殊编译参数（如 `-nostartfiles -nodefaultlibs`）

✅ **无 SELinux 限制**：纯 Perl 模块可在用户目录直接使用，无 HMDFS 加载限制

✅ **易于部署**：打包体积小（64KB），无需 ELF 签名

### 编译要点

1. **依赖安装**：需预先安装所有依赖模块到 PERL5LIB 路径
2. **环境变量**：设置 `PERL5LIB` 包含依赖模块路径
3. **编译命令**：`perl Makefile.PL PREFIX=$DEFAULT_PREFIX && make`
4. **无补丁**：纯 Perl 源码无需修改

### 功能限制

⚠️ **安全模式限制**：复杂过滤器表达式（如 `?(@.price < 10)`）在安全模式下可能受限

建议使用简单路径查询代替复杂过滤器。

## 依赖关系

### 编译依赖

- Carp::Assert 0.21
- Exporter::Tiny 1.006002
- JSON::MaybeXS 1.004008
- LV 0.006
- Readonly 2.05
- Try::Tiny 0.31

### 运行依赖

- Perl 5.42.0+
- JSON::PP 或 JSON::XS（JSON::MaybeXS 自动选择可用后端）

## 参考资料

- **MetaCPAN**: https://metacpan.org/pod/JSON::Path
- **GitHub**: https://github.com/popefelix/perl-json-path
- **JSONPath 规范**: https://goessner.net/articles/JsonPath/
- **编译归档**: archives/p/perl-json-path/1.0.6-r0/

## 示例用法

```perl
use JSON::Path qw(jpath jpath1);

my $data = {
    store => {
        book => [
            { title => "Book 1", price => 10 },
            { title => "Book 2", price => 20 }
        ]
    }
};

# 查询所有书名
my @titles = jpath($data, '$.store.book[*].title');

# 查询单个价格
my $price = jpath1($data, '$.store.book[0].price');
```

## 测试结果

版本 1.0.6-r0 功能测试：
- 总测试数：10
- 通过测试：9
- 成功率：90%
- 核心功能：全部正常

详见 `archives/p/perl-json-path/1.0.6-r0/reports/test-report.md`