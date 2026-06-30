# IO-Stringy

IO::Stringy - Perl I/O on in-core objects like strings and arrays

## 简介

IO::Stringy 是一个 Perl 模块集合，提供对内存中对象（字符串、数组）的 I/O 操作接口。它将字符串和数组包装成文件句柄，可以像操作普通文件一样进行读写操作。

## 已编译版本

| 版本 | 状态 | 编译日期 | 预编译包 |
|------|------|----------|----------|
| 2.113 | built | 2026-06-11 | [下载](2.113/packaging/IO-Stringy-2.113-ohos-aarch64.tar.gz) |

## 模块列表

| 模块 | 说明 |
|------|------|
| IO::Scalar | 对字符串进行文件句柄操作 |
| IO::ScalarArray | 对字符串数组进行文件句柄操作 |
| IO::Lines | 对行数组进行文件句柄操作 |
| IO::AtomicFile | 安全的原子文件写入 |
| IO::InnerFile | 访问大文件内部范围 |
| IO::Wrap | 将任意对象包装成文件句柄 |
| IO::WrapTie | WrapTie 模式的文件句柄包装 |

## 鸿蒙平台适配说明

### 编译特点
- **纯 Perl 模块**: 无 XS 代码，不需要 ELF 签名
- **无补丁**: 无需修改源码即可编译
- **零依赖**: 仅依赖 Perl 核心模块

### 使用方法
```bash
# 设置环境变量
export PERL5LIB=/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0

# Perl 代码中使用
perl -MIO::Scalar -e '
  my $data = "";
  my $fh = IO::Scalar->new(\$data);
  print $fh "Hello!\n";
'
```

### 注意事项
1. **XS 模块冲突**: 如果 site_perl 中存在未签名的 IO XS 模块，需要删除它
2. **环境变量**: 必须正确设置 PERL5LIB

## 测试结果

- 单元测试: PASS (8 文件, 127 测试)
- 功能测试: PASS
- 质量门禁: PASS (G1-G4)

## 相关链接

- CPAN: https://metacpan.org/pod/IO::Stringy
