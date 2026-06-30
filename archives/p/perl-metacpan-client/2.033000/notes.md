# perl-metacpan-client 2.033000 适配笔记

## 编译环境
- 构建系统: ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-06-18
- 编译器: clang/clang++
- Perl 版本: 5.42.0
- 状态: built

## 编译步骤

1. **perl Makefile.PL PREFIX=$DEFAULT_PREFIX** — 生成 Makefile，产生缺失依赖警告
2. **make** — 编译成功，20个 .pm 文件复制到 blib/lib/
3. **make install DESTDIR=$TEST_PREFIX** — DESTDIR 模式 staging 安装成功
4. **make test** — 执行测试套件（详见下文问题）
5. **make install** — 部署到 $DEFAULT_PREFIX 验证成功

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile.PL 报告缺失依赖（Moo, Ref::Util, Safe::Isa, Type::Tiny, JSON::MaybeXS, Test::Needs） | 运行时依赖的 Perl 模块未安装在系统中 | 通过 CPAN 配置 INSTALL_BASE=$DEFAULT_PREFIX 安装所有缺失依赖 |
| 2 | CPAN 安装 XS 依赖（Class::XSAccessor, Cpanel::JSON::XS）失败 | OpenHarmony 平台缺少 sys/types.h 头文件，XS 模块无法编译 | 这些是可选依赖，JSON::MaybeXS 自动回退到 JSON::PP（纯 Perl 实现），Moo 也可纯 Perl 运行 |
| 3 | CPAN 安装模块到系统路径权限被拒 | /data/service/hnp/perl.org/ 目录只读 | 配置 CPAN makepl_arg INSTALL_BASE=/storage/Users/currentUser/usr/local，从 .cpan/build 手动 make install |
| 4 | make test 14/23 测试失败（初版） | `Net::SSLeay.so` 安装在 HMDFS 上，SELinux 标签 `hmdfs` 禁止 .so 动态加载，导致 `IO::Socket::SSL` 失败，HTTPS 全部不可用 | **已解决**：设置 `METACPAN_DOMAIN=http://fastapi.metacpan.org` 环境变量，MetaCPAN::Client 内置支持该环境变量覆盖 API 域名，降级为 HTTP 后全部 261 个测试通过 |

## 源码修改

无补丁，源码未做任何修改。纯 Perl 模块无需适配。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| Moo | 2.005005 | 本次编译安装 |
| Moo::Role | 2.005005 | 随 Moo 安装 |
| Ref::Util | 0.204 | 本次编译安装 |
| Safe::Isa | 1.000010 | 本次编译安装 |
| Type::Tiny | 2.010001 | 本次编译安装 |
| JSON::MaybeXS | 1.004008 | 本次编译安装 |
| Test::Needs | 0.002010 | 本次编译安装 |
| HTTP::Tiny | 0.090 | 已预装 |
| IO::Socket::SSL | 2.085 | 已预装 |
| JSON::PP | 4.16 | 已预装 |
| Net::SSLeay | 1.85 | 已预装 |
| URI::Escape | 5.21 | 已预装 |

## 验证结果

```bash
# 测试命令（关键：METACPAN_DOMAIN 环境变量）
$ METACPAN_DOMAIN=http://fastapi.metacpan.org make test
All tests successful.
Files=23, Tests=261, 95 wallclock secs
Result: PASS

# 模块加载验证
$ perl -MMetaCPAN::Client -e 'print "MetaCPAN::Client version: $MetaCPAN::Client::VERSION\n"'
MetaCPAN::Client version: 2.033000
```

## 注意事项

1. **纯 Perl 模块**：MetaCPAN-Client 是纯 Perl 模块（非 XS），编译过程仅为文件复制，无需 C 编译器
2. **XS 可选依赖跳过**：Class::XSAccessor 和 Cpanel::JSON::XS 因平台缺少 sys/types.h 无法编译，但这些是可选依赖，不影响模块功能
3. **SSL 限制与测试解决方案**：`Net::SSLeay.so` 因 HMDFS SELinux 限制无法加载，导致 HTTPS 不可用。通过 `METACPAN_DOMAIN` 环境变量降级为 HTTP，全部 261 个测试通过
4. **依赖安装路径**：CPAN 需配置 INSTALL_BASE 安装到用户可写目录
---

**编译结束**: 2026-06-18 11:04
**最终状态**: built
