# perl-statistics-chisquare

How well-distributed is your data? Statistics::ChiSquare 是一个纯 Perl 的卡方统计模块，用于判断数据分布的随机性。

## 软件信息

- **官网**: https://github.com/DrHyde/perl-modules-Statistics-ChiSquare
- **源码**: https://github.com/DrHyde/perl-modules-Statistics-ChiSquare
- **许可证**: GPL-2.0-only OR Artistic-1.0
- **分类**: statistics

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.0000-r2 | published | 2026-07-03 | 纯 Perl 模块，无需补丁，conan-verify 全通过 |

## 运行依赖

- perl (5.42.0+)

## 编译依赖

无。纯 Perl 模块无需 C 编译器或外部库。

## 使用说明

Statistics::ChiSquare 提供卡方检验功能，判断数据是否随机分布。

### 安装

通过 Conan 安装：
```bash
conan install --requires=perl-statistics-chisquare/1.0000-r2@ohpcd/stable
```

安装后通过 PERL5LIB 环境变量加载模块。

### 示例

```perl
use Statistics::ChiSquare;
my @data = (500, 500);
print chisquare(@data);
# 输出: There's a >99% chance, and a <100% chance, that this data is random.
```

### 注意事项

- 纯 Perl 模块，在鸿蒙平台上无平台兼容性问题
- 与 XS 模块（如 perl-dbd-pg）不同，无需 CRT 文件绕过或 SELinux 处理
- Conan 配方通过 `runenv_info.append_path("PERL5LIB", ...)` 管理模块搜索路径

---
*OpenHarmony 编译归档 · 2026-07-03*
