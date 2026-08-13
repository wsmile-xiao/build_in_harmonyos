# perl-par-dist

Create and manipulate PAR distributions — pure Perl module for packaging Perl modules into .par archives.

## 软件信息

- **官网**: https://metacpan.org/dist/PAR-Dist
- **源码**: https://github.com/rschupp/PAR-Dist
- **许可证**: MIT
- **分类**: perl

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.53-r0 | built | 2026-07-02 | 纯 Perl 模块，编译成功，功能测试通过 |

## 运行依赖

- perl (5.42.0)

## 编译依赖

- perl (含 ExtUtils::MakeMaker)

## 使用说明

PAR::Dist 是一个纯 Perl 模块，用于创建和操作 PAR 分发包（.par 文件）。PAR 分发包是一种 ZIP 格式的归档文件，包含 Perl 模块及其元数据，可用于跨平台分发 Perl 模块。

### 主要功能

- `parse_dist_name()` — 解析 .par 文件名，提取模块名、版本、架构和 Perl 版本
- `generate_blib_stub()` — 生成 blib 目录骨架和 META.yml
- `blib_to_par()` — 从 blib 目录创建 .par 分发包
- `install_par()` — 安装 .par 分发包到 Perl 系统
- `uninstall_par()` — 卸载已安装的 .par 分发包
- `get_meta()` — 读取 .par 文件中的元数据
- `contains_binaries()` — 检查 .par 是否包含 XS 二进制内容
- `merge_par()` — 合并多个 .par 分发包
- `sign_par()` / `verify_par()` — 签名和验证 .par 文件（需要 Module::Signature）

### 安装

模块安装到 Perl site_perl 目录：`/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/PAR/Dist.pm`

### 注意事项

- 纯 Perl 模块，无 XS 编译，无 SELinux 限制问题
- `sign_par` / `verify_par` 功能需要可选依赖 Module::Signature（未安装）
- `install_par` / `uninstall_par` 正常工作，但自定义 prefix 卸载时 packlist 路径查找有限制

---
*OpenHarmony 编译归档 · 2026-07-03*
