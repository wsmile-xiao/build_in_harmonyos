# perl-ole-storage_lite

OLE::Storage_Lite - Simple Class for OLE document interface.

## 软件信息

- **官网**: https://metacpan.org/dist/OLE-Storage_Lite
- **源码**: https://cpan.metacpan.org/authors/id/J/JM/JMCNAMARA/OLE-Storage_Lite-0.24.tar.gz
- **许可证**: MIT
- **分类**: perl-module

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.24-r0 | built | 2026-07-02 | 纯Perl模块，编译成功，conan-verify全部通过 |

## 运行依赖

- perl (系统自带)

## 编译依赖

无额外依赖。纯 Perl 模块，使用 ExtUtils::MakeMaker (perl Makefile.PL) 构建。

## 使用说明

OLE::Storage_Lite 是一个用于读写 OLE (Object Linking and Embedding) 结构化文件的 Perl 模块。
它支持创建、读取和修改 OLE 文档格式（如 .xls、.doc 等 Microsoft 复合文档格式）。

### 安装

通过 Conan 安装：
```bash
conan install --requires=perl-ole-storage_lite/0.24-r0@ohpcd/stable
```

安装后，Perl 模块位于包的 `lib/perl5/` 目录下，通过 `PERL5LIB` 环境变量自动暴露。

### 注意事项

- 这是纯 Perl 模块，无 C/XS 编译，无链接需求
- 无需特殊平台适配，原始源码可直接编译
- `getPpsSearch` 方法在 `use strict` 模式下存在已知的符号引用问题，不影响其他功能
- 模块自带 199 项测试全部通过

---
*OpenHarmony 编译归档 · 2026-07-02*
