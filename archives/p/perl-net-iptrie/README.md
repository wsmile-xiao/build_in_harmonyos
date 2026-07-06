# perl-net-iptrie (Net::IPTrie)

Perl module for building IPv4 and IPv6 address space hierarchies using a trie (radix tree) data structure.

## 概述

Net::IPTrie 提供了一种高效的 IP 地址前缀树结构，支持：

- IPv4 和 IPv6 双栈地址管理
- 前缀添加与精确查找
- 最长前缀匹配（查找最近的父节点）
- 自定义数据存储
- 树遍历操作

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.7-r5 | built | 2026-06-26 | OpenHarmony 平台适配，14/14 功能测试通过 |

## 构建方式

```bash
# Perl ExtUtils::MakeMaker 构建
perl Makefile.PL PREFIX=/usr INSTALLDIRS=site
make
make test
make install DESTDIR=/path/to/staging
```

## Conan 使用

```bash
# 安装预编译包
conan install --requires=perl-net-iptrie/0.7-r5

# 使用模块
perl -I<path_from_conan> -MNet::IPTrie -e '...'
```

## 依赖

| 依赖 | 最低版本 | 说明 |
|------|---------|------|
| Class::Struct | 0.63 | Perl 核心模块 |
| Scalar::Util | 1.21 | Perl 核心模块 |
| NetAddr::IP | 4.007 | CPAN 模块 |
| Test::More | 0 | Perl 核心模块（测试用） |

## OpenHarmony 平台说明

- **模块类型**: 纯 Perl 模块，无 C/XS 扩展
- **SELinux 限制**: 无（纯 Perl 模块不受 HMDFS 限制）
- **安装方式**: 直接通过 conan install 安装到用户空间
- **已知警告**: "Reference is already weak" 来自 Scalar::Util::weaken，非致命

## 文件结构

```
archives/p/perl-net-iptrie/
├── manifest.yaml              # 软件级元数据
├── README.md                  # 本文件
└── 0.7-r5/
    ├── conanfile.py           # Conan 配方 (CI 输入)
    ├── conandata.yml          # 源码 + SHA256 (CI 输入)
    ├── test_package/          # Conan L1 测试 (CI 输入)
    │   ├── conanfile.py
    │   └── test.pl
    ├── patches/               # 自动生成的 MYMETA 元数据
    ├── manifest.yaml          # 版本级元数据 (AI 元数据)
    ├── notes.md               # 适配笔记 (AI 元数据)
    └── reports/               # 验证报告 (AI 元数据)
        ├── conan-verify-report.md
        ├── conan-create.log
        ├── baseline.json
        ├── test-report.md
        ├── quality-report.md
        └── reviewer-report.md
```

## 许可证

Artistic-1.0-Perl

## 作者

Carlos Vicente <cvicente@cpan.org>
