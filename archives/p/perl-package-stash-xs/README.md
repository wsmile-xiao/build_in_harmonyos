# perl-package-stash-xs

Package::Stash::XS - Package::Stash API 的 XS 实现，提供更快、更正确的包符号表操作。

## 软件信息

- **官网**: https://metacpan.org/dist/Package-Stash-XS
- **源码**: https://cpan.metacpan.org/authors/id/E/ET/ETHER/Package-Stash-XS-0.30.tar.gz
- **许可证**: perl_5
- **分类**: perl-library

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.30-r5 | built | 2026-07-02 | 首次编译成功，conan-verify 通过 |

## 运行依赖

- perl (v5.42.0)
- perl-package-stash (纯 Perl 后端, v0.40)

## 编译依赖

- musl (提供标准 C 库头文件 sys/types.h, endian.h 等)
- clang 18.1.8

## 使用说明

Package::Stash::XS 是 Package::Stash 的 XS (C) 实现，提供比纯 Perl 版本更高的性能。
当 XS 后端不可用时，Package::Stash 会自动回退到纯 Perl (PP) 后端。

### 安装

预编译 HNP 包安装到 `/data/service/hnp/perl.org/perl_5.42.0/` 目录：

```bash
# 需要 installs 用户权限
unzip perl-package-stash-xs.hnp -d /data/service/hnp/perl.org/perl_5.42.0/
```

安装后验证：
```bash
perl -MPackage::Stash::XS -e 'print "XS version: $Package::Stash::XS::VERSION\n"'
# 期望输出: XS version: 0.30
```

### 注意事项

- 鸿蒙系统缺少 CRT 文件 (crti.o, crtn.o 等)，编译时需要 `-nostartfiles -nodefaultlibs` 参数
- 鸿蒙系统缺少标准 C 头文件，需要通过 INC 指向 `_sysheaders_backup` 目录
- 鸿蒙 libc.so 位于 /system/lib64，链接时需要 `-L/system/lib64`
- 由于 SELinux HMDFS 限制，XS 模块的 .so 需要安装到系统目录 `/data/service/hnp` 才能正常加载
- 在 XS 后端不可用时，Package::Stash 自动回退到纯 Perl 后端，功能完全可用

---
*OpenHarmony 编译归档 · 2026-07-02*
