# perl-params-validate

Validate method/function parameters (Perl XS module).

## 软件信息

- **官网**: https://metacpan.org/release/Params-Validate
- **源码**: https://github.com/houseabsolute/params-validate
- **许可证**: Artistic-2.0
- **分类**: perl

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.31 | built | 2026-07-08 | XS+PP 双实现，CI 修复 Module::Build 不可用 |

## 运行依赖

- perl (>= 5.42.0)
- musl (C 标准库头文件)

## 编译依赖

- perl (ExtUtils::MakeMaker，随 Perl 核心提供)
- musl (提供标准 C 库头文件: stdio.h, ctype.h 等)
- clang (鸿蒙系统编译器)

## 使用说明

Params::Validate 是一个 Perl 参数验证模块，提供 XS (C 编译) 和 PP (纯 Perl) 两种实现。
XS 实现性能更高，PP 实现无需编译即可使用。

### 安装

预编译包安装到 Perl 站点目录：
```
/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/
```

### 注意事项

- 源码仅提供 Build.PL (Module::Build)，CI 环境无 Module::Build，改用 Makefile.PL (ExtUtils::MakeMaker)
- 鸿蒙系统缺少 CRT 文件 (crti.o, crtn.o)，XS 编译时需内联传递 -nostartfiles -nodefaultlibs -lc 给 clang
- Perl 5.42.0 的 lddlflags 包含 -fstack-protector-strong，ld.lld 拒绝该参数 (E137)
- musl C 库头文件不在默认搜索路径，需通过 -I 参数添加
- SELinux HMDFS 限制 XS 模块加载，需安装到系统目录 `/data/service/hnp`
- Module::Implementation 自动降级: XS 不可用时自动回退到 PP 模式
- PP 模式功能完全可用 (10/10 测试通过): validate, validate_pos, validate_with, 正则约束, 类型检查

---
*OpenHarmony 编译归档 · 2026-07-03 编译 · 2026-07-06 测试 · 2026-07-08 CI 修复*
