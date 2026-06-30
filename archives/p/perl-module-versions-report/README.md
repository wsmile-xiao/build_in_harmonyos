# perl-module-versions-report

## 软件描述

Module::Versions::Report — 报告 Perl 解释器内存中所有模块的版本信息。

在程序中加入 `use Module::Versions::Report;`，程序退出时会自动输出所有已加载模块的版本报告。也可以通过 `report()` 函数获取报告字符串，或 `print_report()` 直接输出。

## 版本列表

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.06 | published | 2026-06-18 | 纯 Perl 模块，无补丁，全测试通过 |

## 编译特点

- **模块类型**: 纯 Perl (无 XS/C 代码)
- **构建系统**: ExtUtils::MakeMaker (perl Makefile.PL)
- **平台适配**: 无需特殊适配
- **SELinux 影响**: 无 (纯 Perl 不受限制)
- **补丁**: 无
- **依赖**: perl 5.42.0
