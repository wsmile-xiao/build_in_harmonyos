# perl-net-dns-resolver-mock

**Net::DNS::Resolver::Mock** — Mock a DNS Resolver object for testing.

纯 Perl 模块，用于在测试环境中模拟 DNS 解析器对象，避免真实 DNS 查询。

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.20230216-r1 | built | 2026-06-25 | 首次适配 OpenHarmony |

## 功能

Net::DNS::Resolver::Mock 提供以下能力：

- 创建模拟的 DNS Resolver 对象
- 继承自 Net::DNS::Resolver，兼容标准 DNS 查询接口
- 用于单元测试中隔离真实 DNS 依赖

## OHOS 适配

纯 Perl 模块，无需 C 编译，使用 Makefile.PL (ExtUtils::MakeMaker) 构建系统。在鸿蒙平台无需任何源码修改即可编译运行。

适配要点：
- `package()` 中从 `blib/lib` 复制 `.pm` 文件到 Conan 包的 `lib/` 目录
- `package_info()` 通过 `PERL5LIB` 环境变量暴露模块路径供下游使用

## 依赖关系

- **运行时依赖**: Perl 5.42.0
- **编译依赖**: Perl 5.42.0 + ExtUtils::MakeMaker
- 无 C 库依赖

## 参考资料

- [MetaCPAN](https://metacpan.org/dist/Net-DNS-Resolver-Mock)
- [CPAN 源码](https://cpan.metacpan.org/authors/id/M/MB/MBRADSHAW/Net-DNS-Resolver-Mock-1.20230216.tar.gz)
