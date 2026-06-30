# ExtUtils::CChecker

## 简介
Configure-time utilities for using C headers, libraries, or OS features in Perl modules. Helps other Perl modules detect C compiler capabilities during Build.PL/Makefile.PL configuration.

## OHOS 适配
- **纯 Perl 模块**: 无 XS 代码，无需编译 C 代码到原生库
- **测试受限**: 测试脚本尝试编译 C 程序验证功能，OHOS 缺少标准 C 运行时库（crt*.o, libunwind）
- **安装方式**: `./Build install`（跳过测试）
- **依赖**: perl 5.14+, ExtUtils::CBuilder, Module::Build

## 功能验证
```bash
perl -MExtUtils::CChecker -e 'print "ExtUtils::CChecker version: $ExtUtils::CChecker::VERSION\n"'
```

## 排除与替代
- 测试套件跳过（`./Build test` 会因链接错误失败）
- 保留模块核心功能，用于其他 Perl 模块的 configure 阶段

## 参考
- CPAN: https://metacpan.org/pod/ExtUtils::CChecker
- 源码: https://cpan.metacpan.org/authors/id/P/PE/PEVANS/ExtUtils-CChecker-0.12.tar.gz
