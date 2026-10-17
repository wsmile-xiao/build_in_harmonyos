# perl-par-packer

PAR::Packer — 将 Perl 程序打包为独立可执行文件或 .par 归档。

## 版本

- 1.064-r2 (2026-07-03)

## 描述

PAR::Packer 是 Perl 的打包工具，可以将 Perl 脚本及其依赖模块打包为独立的可执行文件 (parl) 或 .par 归档文件。基于 PAR (Perl Archive) 框架，支持 XS 模块和纯 Perl 模块。

## 构建系统

- Perl ExtUtils::MakeMaker (Makefile.PL)
- 包含 XS 代码 (C/XS 编译为 .so) 和 C 可执行文件 (myldr/parl)

## 依赖

- Perl 5.42.0 (静态链接, libperl.a)
- PAR 1.021
- Archive::Zip 1.68
- Getopt::ArgvFile 1.11
- ExtUtils::Depends 0.8002
- Module::ScanDeps 1.37
- OHOS SDK 26.0.0.18 (sysroot)
- clang 18.1.8

## OHOS 平台适配

### 关键修复

1. **CRT 文件缺失**: 使用 `-nostartfiles -nodefaultlibs -lc` 绕过 (同 perl-dbd-pg)
2. **-fstack-protector-strong**: ld.lld 不识别，从 ldflags 中移除
3. **off64_t 未定义**: 添加 `-Doff64_t=off_t`
4. **sysroot 指定**: 使用 OHOS SDK sysroot 获取系统头文件
5. **ldd 命令缺失**: 创建 readelf wrapper 脚本
6. **HMDFS 安全目录检查**: 使用 `PAR_GLOBAL_TEMP` 环境变量绕过 `par_mktmpdir()` 的 `isSafeDir()` 检查
7. **CBuilder 检测失败**: 强制 `$have_cc = 1`

### 平台限制

- parl/parldyn 无法独立执行（签名失效）
- pp -o 无法创建独立可执行文件
- PAR 模块运行时临时目录创建失败
- XS .so 在 HMDFS 上无法动态加载（需安装到系统目录）

### 推荐使用方式

```bash
# 打包为 .par 文件
perl -I<lib_path> pp -p -o script.par script.pl

# 运行 .par 文件
perl -I<lib_path> par.pl script.par [args...]
```

## 补丁

5 个补丁文件，均为 OHOS 平台适配:
- 0001-Makefile.PL.patch: 主 Makefile.PL 适配
- 0002-myldr-Makefile.PL.patch: myldr Makefile.PL 适配
- 0003-0005: 测试 XS 模块 Makefile.PL 适配
