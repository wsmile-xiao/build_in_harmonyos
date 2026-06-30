# perl-module-metadata 1.000038 适配笔记

## 编译环境
- 构建系统: custom-perl (ExtUtils::MakeMaker / Makefile.PL)
- 编译日期: 2026-06-18
- 编译器: clang/clang++ (纯 Perl 模块，无 C 编译)
- Perl 版本: 5.42.0 (aarch64-linux)
- 平台: OpenHarmony (aarch64-unknown-linux-ohos)
- 状态: published

## 软件简介

Module::Metadata 是 Perl 核心工具链模块，用于从 Perl 模块文件中收集包名和 POD 信息。它是 CPAN 客户端、Module::Build、Dist::Zilla 等工具的底层依赖。

## 编译步骤

### 1. 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build perl-module-metadata 1.000038
```
从 CPAN 下载 Module-Metadata-1.000038.tar.gz，解压到 ~/tmp/builds/perl-module-metadata-1.000038.work。

### 2. 编译与安装
```bash
cd ~/tmp/builds/perl-module-metadata-1.000038.work
perl Makefile.PL
make
make install DESTDIR=$TEST_PREFIX
```

这是一个纯 Perl 模块，使用 ExtUtils::MakeMaker 构建系统：
- `perl Makefile.PL` 生成 Makefile
- `make` 不需要编译 C/XS 代码
- `make install DESTDIR=$TEST_PREFIX` 将模块安装到 staging 目录

### 3. 预编译包制作
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package perl-module-metadata 1.000038
```
打包产物：perl-module-metadata-1.000038-ohos-aarch64.tar.gz (42KB)

### 4. 部署到本地
```bash
make install  # 安装到 ~/usr/local
```

### 5. 收尾
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py finish perl-module-metadata 1.000038 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 | 纯 Perl 模块，无平台兼容性问题 | 无需任何修复 |

本模块为纯 Perl 实现，不涉及 C/XS 编译、不生成共享库 (.so)，因此：
- 无 config.guess/config.sub 平台识别问题
- 无 SELinux HMDFS 限制（对比 perl-dbd-pg 的 XS 模块加载问题）
- 无 ELF 签名需求
- 无链接器/CRT 文件缺失问题

## 源码修改

无。本模块无需任何补丁，源码完全兼容 OpenHarmony 平台。

## 依赖版本

### 运行时依赖
| 模块 | 要求版本 | 实际版本 | 状态 |
|------|---------|---------|------|
| perl | 5.006 | 5.42.0 | ✅ |
| Carp | any | 1.54 | ✅ |
| Encode | any | 3.21 | ✅ |
| Fcntl | any | 1.20 | ✅ |
| File::Find | any | 1.44 | ✅ |
| File::Spec | any | 3.94 | ✅ |
| version | 0.87 | 0.9933 | ✅ |
| strict | any | 1.14 | ✅ |
| warnings | any | 1.74 | ✅ |

### 构建依赖
| 模块 | 要求版本 | 实际版本 | 状态 |
|------|---------|---------|------|
| ExtUtils::MakeMaker | any | 7.76 | ✅ |

所有依赖均为 Perl 核心模块，随 Perl 5.42.0 预装，无需额外安装。

## 验证结果

### make test 结果
```bash
$ make test
All tests successful.
Files=9, Tests=385, 3 wallclock secs
Result: PASS
```

### 功能测试结果
```bash
$ perl test_module_metadata_v3.pl
1..20
# 全部 22 项功能测试通过
```

### 模块加载验证
```bash
$ perl -MModule::Metadata -e 'print Module::Metadata->VERSION'
1.000038
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/perl-module-metadata-1.000038-ohos-aarch64.tar.gz | 42KB | 预编译包 |
| lib/Module/Metadata.pm | 34KB | 模块文件 |
| lib/perl5/aarch64-linux/auto/Module/Metadata/.packlist | - | 安装清单 |

## 注意事项

1. **纯 Perl 模块**：本模块不含 XS/C 代码，在鸿蒙平台上无兼容性问题。
2. **与 perl-dbd-pg 的差异**：perl-dbd-pg 因包含 XS 模块 (.so) 遇到 SELinux HMDFS 限制，需要管理员安装到系统目录；本模块纯 Perl 实现可直接从 `~/usr/local/lib/perl5` 加载，无需特殊处理。
3. **pod() 方法**：使用 `pod()` 方法需在 `new_from_file` 时传入 `collect_pod => 1` 参数，否则返回 undef。这是模块 API 设计，非平台问题。
4. **核心模块依赖**：所有运行时依赖均为 Perl 核心模块，不需要额外安装第三方库。

---

**编译结束**: 2026-06-22
**最终状态**: published
