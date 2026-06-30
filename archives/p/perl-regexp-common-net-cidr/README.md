# perl-regexp-common-net-cidr

Regexp::Common::net::CIDR — Provide patterns for CIDR (Classless Inter-Domain Routing) blocks.

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.03 | published | 2026-06-26 |

## 描述

Regexp::Common::net::CIDR 是 Regexp::Common 的扩展模块，提供 CIDR 块的正则表达式模式。支持 IPv4 CIDR 格式的匹配，包括标准格式（192.168.1.0/24）和缩写格式（10/8、10.0/8）。

## 特性

- 纯 Perl 模块，无 XS/C 代码
- 依赖 Regexp::Common (perl-regexp-common/2024080801@ohpcd/stable)
- 构建系统: ExtUtils::MakeMaker (替换原始 Module::Install)
- 许可证: Perl 5 (perl_5)
- 支持 IPv4 CIDR 模式匹配
- 支持 -keep 选项提取网络地址和掩码

## 鸿蒙平台适配

- 平台: HarmonyOS (aarch64)
- 编译器: clang/clang++
- 原始 Makefile.PL 使用 Module::Install，在隔离环境中触发自动安装，已替换为标准 ExtUtils::MakeMaker
- 无需源码补丁（在 conanfile.py build() 中动态生成替换的 Makefile.PL）
- Conan 配方: `perl-regexp-common-net-cidr/0.03@ohpcd/stable`
- Conan 依赖: `perl-regexp-common/2024080801@ohpcd/stable`
