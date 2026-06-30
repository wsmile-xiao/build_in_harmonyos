# perl-json-xs

JSON::XS - JSON serialising/deserialising for Perl

## 软件描述

JSON::XS 是一个高性能的 Perl JSON 编码/解码模块，使用 XS（C 扩展）实现，提供比纯 Perl 版本快数倍的性能。

主要功能：
- 将 Perl 数据结构编码为 JSON 字符串
- 将 JSON 字符串解码为 Perl 数据结构
- 支持 UTF-8 编码
- 支持增量解析
- 提供布尔值类型（JSON::XS::Boolean）

## 编译版本

| 版本 | 状态 | 编译日期 | 质量门禁 |
|------|------|---------|---------|
| 4.04 | built | 2026-06-13 | ✅ PASS |
| 4.04-r0 | built | 2026-06-12 | ⚠️ FAIL |

推荐使用版本: **4.04**

## 依赖关系

### 编译依赖
- Perl 5.42.0
- Canary::Stability 2013
- common::sense 3.75
- Types::Serialiser 1.01

### 运行时依赖
- Perl 5.42.0
- common::sense 3.75
- Types::Serialiser 1.01

## 平台兼容性

| 平台 | 状态 | 备注 |
|------|------|------|
| OpenHarmony (aarch64) | ✅ 编译成功 | XS 模块需管理员安装 |
| Linux (x86_64) | ✅ 参考 CPAN | 标准支持 |

## 安装说明

### 预编译包安装（推荐）

管理员需要将预编译包安装到系统目录：

```bash
# 1. 解压预编译包
sudo -u installs tar -xzf perl-json-xs-4.04-ohos-aarch64.tar.gz -C /data/service/hnp/perl.org/perl_5.42.0/

# 2. 重新签名 XS.so
/data/service/hnp/bin/binary-sign-tool sign \
  -inFile /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/JSON/XS/XS.so \
  -outFile /tmp/XS.so.signed -selfSign 1

# 3. 替换签名文件
sudo -u installs mv /tmp/XS.so.signed \
  /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/JSON/XS/XS.so

# 4. 验证安装
perl -MJSON::XS -e 'print $JSON::XS::VERSION'
# 预期输出: 4.04
```

### SELinux 限制说明

在 OpenHarmony 平台上，XS 模块（.so 文件）在用户目录无法加载，这是 SELinux HMDFS 的限制。必须由管理员安装到系统目录 `/data/service/hnp/` 才能正常使用。

这是所有 Perl XS 模块的共同限制，不影响编译产物的可用性。

## 使用示例

```perl
use JSON::XS;

# 编码
my $json = encode_json({
    name => 'OpenHarmony',
    version => '4.04',
    features => ['JSON', 'XS', 'high-performance']
});
print $json;
# 输出: {"name":"OpenHarmony","version":"4.04","features":["JSON","XS","high-performance"]}

# 解码
my $data = decode_json($json);
print $data->{name};  # OpenHarmony

# 布尔值
my $bool_json = encode_json({ enabled => JSON::XS::true });
print $bool_json;  # {"enabled":true}

# 增量解析
my $xs = JSON::XS->new;
$xs->incr_parse('[1, 2, 3]');
while (my $obj = $xs->incr_parse) {
    print "Parsed: @$obj\n";
}
```

## 性能特点

- **高速编码**: XS 实现比纯 Perl 版本快 2-5 倍
- **内存效率**: 优化的内存管理，适合大数据处理
- **UTF-8 支持**: 正确处理 Unicode 字符
- **类型转换**: 自动处理 Perl 与 JSON 类型差异

## 相关资源

- [CPAN - JSON::XS](https://metacpan.org/pod/JSON::XS)
- [GitHub - JSON-XS](https://github.com/mlehmann/JSON-XS)
- [编译归档](./4.04/) - 详细的编译记录和测试报告