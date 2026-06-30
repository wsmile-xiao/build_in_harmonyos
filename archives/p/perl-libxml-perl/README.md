# perl-libxml-perl

## 简介

libxml-perl 是一组基于 XML::Parser 的 Perl SAX/XML 处理器，提供了多种 XML 解析和处理的接口模块。

## OHOS 适配

### 适配要点

- **纯 Perl 模块**：无需 C 编译器，只需 Perl 环境即可安装和使用
- **依赖建议**：建议先安装 XML::Parser 模块以获得完整功能
- **环境配置**：用户需设置 `PERL5LIB` 环境变量指向模块安装路径

### 已知问题

- 无已知问题，模块在鸿蒙平台完全可用

## 依赖

### 编译依赖
- Perl 5.42.0

### 运行依赖（可选）
- XML::Parser 2.19（推荐安装）

## 功能验证

### 已验证功能
- ✅ XML::ESISParser 模块加载
- ✅ XML::Perl2SAX 模块加载
- ✅ Data::Grove 模块加载
- ✅ XML::Handler::Subs 模块加载
- ✅ XML::SAX2Perl 模块加载
- ✅ XML::PatAct::* 模块加载
- ✅ Data::Grove::Parent 模块加载

### 测试方法

```bash
# 设置 PERL5LIB 环境变量
export PERL5LIB=~/usr/local/lib/site_perl/5.42.0

# 验证模块可用性
perl -e "use XML::ESISParser; print 'OK\n'"
```

## 参考

- CPAN: https://metacpan.org/pod/libxml-perl
- 源码: https://mirrors.tuna.tsinghua.edu.cn/CPAN/modules/by-module/XML/KMACLEOD/libxml-perl-0.08.tar.gz