# perl-module-cpmfile

Perl module for parsing cpmfile (cpm.yml) dependency format.

## 描述

Module::cpmfile 是一个 Perl 模块，用于解析 cpmfile 文件格式（通常保存为 `cpm.yml`）。
cpmfile 是描述 Perl 模块依赖关系的文件格式，主要被 [App::cpm](https://metacpan.org/pod/App::cpm) 使用。

该模块提供以下核心功能：
- 从 cpm.yml 文件加载依赖定义
- 将 CPAN::Meta 数据结构转换为 cpmfile 格式
- 获取有效的依赖需求（按 phase/type 过滤）
- 支持 optional features
- 序列化为字符串

## 版本历史

| 版本 | 日期 | 状态 | 备注 |
|------|------|------|------|
| 0.006 | 2026-06-18 | published | OpenHarmony aarch64 平台编译通过 |

## 构建系统

- **构建系统**: Module::Build::Tiny (perl-build-tiny)
- **模块类型**: 纯 Perl（无 XS/C 代码）
- **编译器**: 无需（纯 Perl 实现）

## 依赖

### 运行时依赖
- perl >= 5.008001
- YAML::PP >= 0.036
- CPAN::Meta (Perl 核心模块)
- Scalar::Util (Perl 核心模块)

### 构建依赖
- Module::Build::Tiny >= 0.047
- perl >= 5.008001

## 平台兼容性

### OpenHarmony (aarch64-unknown-linux-ohos)

✅ **完全兼容**

- 纯 Perl 模块，不依赖 XS/C 扩展
- 不受 SELinux HMDFS 限制（无需加载 .so 文件）
- 不需要 CRT 文件（无 C 链接）
- 无需平台适配补丁
- 模块自带测试套件全部通过（3 文件，8 测试）

### 与其他 Perl 模块对比

| 特性 | perl-dbd-pg (XS) | perl-module-cpmfile (PurePerl) |
|------|-------------------|-------------------------------|
| 模块类型 | XS (C 扩展) | 纯 Perl |
| SELinux 限制 | ❌ 需管理员安装 | ✅ 无影响 |
| 需要补丁 | 是 (2 个) | 否 (0 个) |
| 预编译包 | 需特殊处理 | 标准打包 |

## 使用示例

```perl
use Module::cpmfile;

# 从 cpm.yml 文件加载
my $cpmfile = Module::cpmfile->load("cpm.yml");

# 获取运行时依赖
my $reqs = $cpmfile->effective_requirements(undef, ["runtime"], ["requires"]);

# 获取所有 phase 的依赖
my $all_reqs = $cpmfile->effective_requirements(
    undef,
    ["runtime", "configure", "test", "develop"],
    ["requires", "recommends", "suggests"]
);

# 检查 features
if (my $features = $cpmfile->features) {
    for my $id (keys %$features) {
        print "Feature: $id - $features->{$id}{description}\n";
    }
}

# 序列化为字符串
print $cpmfile->to_string;
```

## 许可证

Perl (Artistic License 1.0 or GPL)
