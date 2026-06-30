# perl-module-build-xsutil

Module::Build::XSUtil — A Module::Build class for building XS modules

## 描述

Module::Build::XSUtil 是 Module::Build 的子类，专门用于构建 XS (C/C++ 扩展) 模块。它提供以下功能：

- 自动生成 ppport.h（通过 Devel::PPPort）
- 自动生成 xshelper.h（XS 辅助头文件）
- 编译器检测（C/C++）
- C99 编译器支持检测
- C++ 编译器支持检测
- 编译警告标志管理
- 调试构建支持（-g 选项）

## 版本历史

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 0.19 | published | 2026-06-18 | OpenHarmony 平台适配，含链接器修复补丁 |

## OpenHarmony 适配说明

### 平台修复补丁 (0001-fix-ohos-linker-flags.patch)

本模块在 OpenHarmony 平台上需要补丁修复以下问题：

1. **链接器标志兼容性**: Perl 配置中的 `-fstack-protector-strong` 被放在 ldflags/lddlflags 中，但 ld.lld 不支持此标志（它是编译器标志）。补丁通过覆盖 `cbuilder()` 方法传递修复后的 Config。

2. **系统库搜索路径**: OpenHarmony 的系统库（libc, libunwind）不在 ld.lld 默认搜索路径中。补丁添加 `-L/system/lib64 -L$HOME/usr/local/lib` 路径。

3. **musl 头文件路径**: 系统 C 库头文件（sys/types.h 等）位于 musl 安装目录。补丁添加 `-I$HOME/usr/local/include` 到 ccflags。

4. **编译器检测缓存**: Module::Build 在 `SUPER::new()` 中预检测编译器，失败结果被缓存。补丁清除缓存确保使用修复后的配置重新检测。

### SELinux 限制

XS 模块的 .so 文件从 HMDFS 路径（如 ~/usr/local/lib）加载时会被 SELinux 拒绝。需要安装到系统目录 (/data/service/hnp) 才能正常加载。此限制与 perl-dbd-pg 相同，是 OpenHarmony 平台特性。

## 使用方法

```perl
use Module::Build::XSUtil;

my $builder = Module::Build::XSUtil->new(
    dist_name            => 'Your-XS-Module',
    license              => 'perl',
    dist_version_from    => 'lib/Your/XS/Module.pm',
    generate_ppport_h    => 'lib/Your/XS/ppport.h',
    generate_xshelper_h  => 'lib/Your/XS/xshelper.h',
    needs_compiler_c99   => 1,
);

$builder->create_build_script();
```

## 依赖

- Perl 5.8.1+
- Module::Build 0.4234+
