# perl-sort-key

Sort::Key - the fastest way to sort anything in Perl (XS module).

## 软件信息

- **官网**: https://metacpan.org/dist/Sort-Key
- **许可证**: Artistic-1.0-Perl OR GPL-1.0-or-later
- **分类**: perl
- **作者**: Salvador Fandino <sfandino@yahoo.com>

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.33 | published | 2026-07-01 | XS 模块编译成功，conan-verify 全门禁通过 |

## 运行依赖

- perl

## 编译依赖

- perl (提供 perl 解释器和 ExtUtils::MakeMaker)

## 使用说明

Sort::Key 是一个 Perl XS 模块，提供高性能的排序功能。它通过 XS (C 扩展) 实现，
比纯 Perl 排序快得多。支持多种排序模式：

- `keysort` - 按计算键排序
- `nkeysort` / `rnkeysort` - 数值排序 / 逆序
- `ikeysort` / `rikeysort` - 整数排序 / 逆序
- `ukeysort` / `rukeysort` - 无符号整数排序 / 逆序
- `nsort` / `rnsort` - 直接数值排序
- `Sort::Key::Multi` - 多键排序
- `Sort::Key::Natural` - 自然排序

### 安装

Conan 安装：
```bash
conan install --requires=perl-sort-key/1.33@ohpcd/stable
```

产物路径：
- `lib/perl5/aarch64-linux/Sort/Key.pm`
- `lib/perl5/aarch64-linux/auto/Sort/Key/Key.so`

### 注意事项

由于鸿蒙系统缺少 CRT 文件（crti.o, crtn.o 等），编译时需要
`-nostartfiles -nodefaultlibs -lc` 链接参数。这与 perl-dbd-pg 的处理方式一致。

由于 SELinux HMDFS 限制，XS 模块（.so 文件）可能需要安装到系统目录
`/data/service/hnp` 才能正常加载。

---
*OpenHarmony 编译归档 · 2026-07-01*
