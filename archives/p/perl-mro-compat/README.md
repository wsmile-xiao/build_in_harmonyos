# perl-mro-compat (MRO::Compat)

MRO::Compat 是一个 Perl 模块，为不同 Perl 版本间的 Method Resolution Order（方法解析顺序）接口提供统一的兼容层。在 Perl 5.10+ 上，它委托给内置的 `mro::*` 函数；在旧版本 Perl 上，它提供自己的实现。

## 功能概述

- 提供 `mro::get_linear_isa`、`mro::set_mro`、`mro::get_mro` 等函数的统一接口
- 支持 C3 和 DFS 两种方法解析顺序
- 提供 `next::method`、`maybe::next::method` 等方法链调用
- 兼容 Perl 5.6+ 的所有版本

## OHOS 适配

### 适配要点

- **纯 Perl 模块**：无需 C 编译，`make` 只复制 `.pm` 文件到 blib 目录
- **构建命令**：使用 `perl Makefile.PL PREFIX=$DEFAULT_PREFIX` 而非 `./configure --prefix=`
- **无补丁**：源码无需任何修改即可在 OpenHarmony 平台编译安装
- **无 SELinux 限制**：因为是纯 Perl 模块（无 .so 文件），不受 HMDFS SELinux 限制影响
- **G0 验证**：G0 clean-verify 不适用于 Perl 模块（无 `./configure` 脚本），通过手动验证替代

### 已知问题

- SSL 证书验证问题可能导致下载失败，使用 `curl -kSL` 绕过
- 上游 CPAN 版本为 0.15，`-r2` 为打包修订版本号

### 与 Linux 的差异

无差异。纯 Perl 模块在任何有 Perl 解释器的平台上行为一致。

## 依赖关系

### 编译依赖

- perl 5.42.0（系统自带，通过 HNP 安装）

### 运行依赖

- perl 5.42.0

## 参考资料

- CPAN: https://metacpan.org/pod/MRO::Compat
- 源码: https://cpan.metacpan.org/authors/id/H/HA/HAARG/MRO-Compat-0.15.tar.gz
