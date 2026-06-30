# perl-rt-extension-commandbymail 3.02 适配笔记

## 编译环境
- 构建系统: perl (ExtUtils::MakeMaker)
- 编译日期: 2026-06-29
- 编译器: clang/clang++
- Perl 版本: 5.42.0 (aarch64-linux)
- 状态: published

## 编译步骤

RT::Extension::CommandByMail 是 RT (Request Tracker) 的邮件命令扩展模块。
原始 Makefile.PL 使用 Module::Install + RTx()，需要 RT 在 configure 时已安装。
通过补丁替换为标准 EUMM Makefile.PL，绕过 RT 运行时依赖：

```bash
# 补丁将 Makefile.PL 从 Module::Install 替换为标准 ExtUtils::MakeMaker
# 然后：
perl Makefile.PL INSTALLDIRS=site
make -j1
# 打包：从 blib/lib 复制 .pm 文件
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `perl Makefile.PL` 提示找不到 RT.pm | 原始 Makefile.PL 使用 Module::Install + RTx()，需要 RT 在 configure 时已安装 | 补丁 0001-Makefile.PL.patch 替换为标准 EUMM Makefile.PL |
| 2 | `apply_conandata_patches()` 未应用补丁 | Conan 2.29.1 (OHOS 适配版) 的补丁导出机制未正确传递补丁文件到构建目录 | conanfile.py 中添加 fallback：检测 Makefile.PL 是否仍含 Module::Install，若是则内联写入 EUMM 版本 |
| 3 | conandata.yml patches 为空但实际有补丁 | 初始自动化生成时未填充补丁信息 | 手动更新 conandata.yml 引用补丁文件 |

## 源码修改

### 补丁: 0001-Makefile.PL.patch
- **文件**: Makefile.PL
- **类型**: 平台适配 (portability)
- **说明**: 将 Module::Install + RTx() 的 Makefile.PL 替换为标准 ExtUtils::MakeMaker 版本
- **原因**: 原始 Makefile.PL 需要 RT 在 configure 时已安装，这在打包阶段不可行
- **效果**: 使模块可以在不安装 RT 的情况下打包 .pm 文件

## 依赖版本

### 编译依赖
- Perl 5.42.0 (系统预装，路径 /data/service/hnp/bin/perl)
- 无其他编译依赖（纯 Perl 模块，无 XS/C 代码）

### 运行时依赖
- RT (Request Tracker) 4.4+ — 核心依赖，提供 RT.pm, RT::EmailParser 等
- Email::Address — 邮件地址解析
- Role::Basic — 角色组合功能

## 验证结果

### Conan 验证
```bash
$ conan create . --user ohpcd --channel stable -pr:h ohos-aarch64 -pr:b ohos-aarch64
# G0-G4 全部 PASS, L2/L4/L5 全部 PASS
# test_package: All 4 .pm files verified
# Module file located successfully (RT runtime dependency expected to be missing)
```

### 功能测试
```bash
# 文件完整性: 4/4 .pm 文件存在 ✅
# Perl 语法: Test.pm syntax OK ✅ (其余模块因 RT 依赖预期失败)
# 模块版本: 3.02 ✅
# PERL5LIB 集成: 4/4 模块可定位 ✅
```

详见: reports/test-report.md

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/perl5/RT/Extension/CommandByMail.pm | 38677 bytes | 核心模块 — 邮件命令处理 |
| lib/perl5/RT/Extension/CommandByMail/Test.pm | 1051 bytes | 测试辅助模块 |
| lib/perl5/RT/Interface/Email/Action/CommandByMail.pm | 1776 bytes | 邮件动作处理 |
| lib/perl5/RT/Interface/Email/Filter/TakeAction.pm | 2652 bytes | 邮件过滤器 — 执行动作 |

## 注意事项

1. 此模块为纯 Perl 实现，不包含 XS 代码，无需 ELF 签名，不受鸿蒙 CRT 文件缺失影响。
2. 参考 perl-dbd-pg 编译经验：纯 Perl 模块在鸿蒙平台无需 `-nostartfiles -nodefaultlibs -lc` 等特殊链接参数。
3. 模块运行时依赖 RT (Request Tracker)，打包阶段仅需安装 .pm 文件，RT 在运行时由用户环境提供。
4. conanfile.py build() 中包含 fallback 机制：先尝试 apply_conandata_patches()，若失败则检测并内联写入 EUMM Makefile.PL。
5. conanfile.py package_info() 设置 PERL5LIB 环境变量，确保消费者通过 conanrun 环境自动获取正确的 Perl 模块搜索路径。
---

**编译结束**: 2026-06-29 19:00
**最终状态**: published
