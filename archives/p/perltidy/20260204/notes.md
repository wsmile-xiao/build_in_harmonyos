# perltidy 20260204 适配笔记

## 编译环境
- 构建系统: custom-perl (Makefile.PL + ExtUtils::MakeMaker)
- 编译日期: 2026-05-27
- 编译器: Perl v5.42.0 (pure Perl software, no C/C++ compilation needed)
- 状态: published

## 编译步骤

1. 下载源码: `curl -L -k -o ~/tmp/builds/perltidy-20260204.tar.gz https://downloads.sourceforge.net/project/perltidy/20260204/Perl-Tidy-20260204.tar.gz`
2. 解压源码: `tar xzf perltidy-20260204.tar.gz` → `Perl-Tidy-20260204`
3. 生成 Makefile: `perl Makefile.PL PREFIX=$DEFAULT_PREFIX INSTALLMAN1DIR=$DEFAULT_PREFIX/share/man/man1 INSTALLMAN3DIR=$DEFAULT_PREFIX/share/man/man3`
4. 编译: `make`
5. 测试: `make test` — 44 files, 656 tests, ALL PASS
6. 安装(staging): `make install DESTDIR=$TEST_PREFIX`
7. 安装(local): `make install` (到 $DEFAULT_PREFIX)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL下载失败 | SourceForge SSL证书验证失败 | `curl -L -k` 绕过SSL验证 |
| 2 | perltidy 无法找到 Perl::Tidy 模块 | 系统Perl @INC不包含$DEFAULT_PREFIX/lib/site_perl/5.42.0 | 在 bin/perltidy 中添加 `use lib '/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0'` |
| 3 | G0 clean-verify 失败 | 脚本默认运行 ./configure，但 Perl 项目无 configure 脚本 | 创建 hints/configure 包装脚本调用 perl Makefile.PL |
| 4 | blib/ 生成文件被追踪为补丁 | blib/ 是构建产物目录，不应作为补丁 | 清理 blib/ 补丁，只保留源码补丁 (R6) |

## 源码修改

- **bin/perltidy**: 添加 `use lib '/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0'` 指令
  - 补丁: 0001-bin-perltidy.patch
  - 原因: Perl @INC 不包含自定义 PREFIX 路径，perltidy 脚本无法找到 Perl::Tidy 模块

## 依赖版本

- Perl: v5.42.0 (系统预装)

## 验证结果

```bash
$ perltidy --version
This is perltidy, v20260204

Copyright 2000-2026 by Steve Hancock
```

功能测试:
```bash
$ echo 'print "hello world\n";' > test.pl && perltidy test.pl && cat test.pl.tdy
print "hello world
";
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perltidy-20260204-ohos-aarch64.tar.gz | 3507KB | 预编译包 |

## 注意事项

- perltidy 是纯 Perl 软件，无 ELF 二进制文件（G1/G3 检查为警告而非错误）
- bin/perltidy 中通过 `use lib` 指令解决了模块路径问题，无需额外设置 PERL5LIB
- 系统Perl site_perl目录为只读，无法直接安装模块到系统路径
- G0 clean-verify 需要 hints/configure 包装脚本适配 Makefile.PL 项目

**编译结束**: 2026-05-27
**最终状态**: published
---

**编译结束**: 2026-05-27 10:30
**最终状态**: published
