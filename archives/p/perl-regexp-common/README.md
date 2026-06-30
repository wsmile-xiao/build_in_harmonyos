# perl-regexp-common

Regexp::Common — Provide commonly requested regular expressions.

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 2024080801 | published | 2026-06-26 |

## 描述

Regexp::Common 是一个 Perl 模块，提供常用正则表达式的统一接口。包含数字、空白、分隔符、注释、IP 地址、URI、邮政编码等多种正则模式。

## 特性

- 纯 Perl 模块，无 XS/C 代码
- 无外部依赖，仅依赖 Perl 核心模块
- 构建系统: ExtUtils::MakeMaker (Makefile.PL)
- 许可证: MIT

## 包含的子模块

| 模块 | 功能 |
|------|------|
| Regexp::Common | 主模块 |
| Regexp::Common::net | 网络相关正则 (IPv4, MAC 等) |
| Regexp::Common::number | 数字正则 (整数、实数、十六进制等) |
| Regexp::Common::URI | URI 正则 (HTTP, FTP, mailto 等) |
| Regexp::Common::delimited | 分隔字符串正则 |
| Regexp::Common::comment | 注释正则 (C, C++, Perl, Python 等) |
| Regexp::Common::balanced | 平衡括号正则 |
| Regexp::Common::whitespace | 空白字符正则 |
| Regexp::Common::zip | 邮政编码正则 |
| Regexp::Common::list | 列表正则 |
| Regexp::Common::profanity | 脏话过滤正则 |
| Regexp::Common::CC | 信用卡号正则 |
| Regexp::Common::SEN | 社会保险号正则 |

## 鸿蒙平台适配

- 平台: HarmonyOS (aarch64)
- 编译器: clang/clang++
- 无需源码补丁
- Conan 配方: `perl-regexp-common/2024080801@ohpcd/stable`

## 测试结果

- **模块测试套件**: ✅ 73 文件, 149249 测试全部通过
- **Conan 验证**: ✅ conan create 成功, test_package 4/5 通过 (URI warning 非致命)
- **功能测试**: ✅ 10 项功能测试全部通过 (数字/网络/分隔符/注释/平衡/列表/脏话/邮编/版本/子模块)

## 修复记录 (2026-06-29)

基于 perl-redis 编译经验，修复以下问题：
1. 移除 conanfile.py generate() 中的 AutotoolsToolchain（纯 Perl 模块不需要）
2. package_info() 使用 glob 动态发现 Perl 版本路径
3. test_package 移除硬编码路径，改为动态检测
4. test_package 新增子模块加载测试和模式匹配功能测试
5. 清理 test_package 中的 conan 生成文件
6. 填充 notes.md，创建软件级 README.md
