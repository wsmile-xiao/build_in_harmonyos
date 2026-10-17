# perl-spreadsheet-parseexcel

Perl module Spreadsheet::ParseExcel — Read information from an Excel .xls file.

## 软件信息

- **官网**: https://metacpan.org/dist/Spreadsheet-ParseExcel
- **源码**: https://github.com/jmcnamara/spreadsheet-parseexcel
- **许可证**: Artistic-1.0-Perl OR GPL-1.0-or-later
- **分类**: data

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.66 | built | 2026-07-01 | 纯 Perl 模块，无需补丁，首次编译成功 |

## 运行依赖

- perl (5.42.0+)
- perl-ole-storage-lite (OLE::Storage_Lite >= 0.19)
- Crypt::RC4 (加密 Excel 支持)
- Digest::Perl::MD5 (加密 Excel 支持)
- IO::Scalar / IO::Stringy (OLE 依赖)

## 编译依赖

- perl (Perl 解释器 + ExtUtils::MakeMaker)

## 测试结果

- 官方测试套件: 32 文件 / 1605 子测试 / 100% 通过
- 功能测试: Excel 97/95 文件解析、错误处理、Utility 函数 — 全部通过

## 使用说明

Spreadsheet::ParseExcel 是一个纯 Perl 模块，用于读取 Excel .xls 文件中的数据。
支持 Excel 95/97/2000 格式，可提取单元格内容、格式信息、图表等。

### 安装

预编译包安装到 `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/Spreadsheet/` 目录。

### 基本用法

```perl
use Spreadsheet::ParseExcel;
my $parser = Spreadsheet::ParseExcel->new();
my $workbook = $parser->parse('file.xls');
for my $worksheet ($workbook->worksheets()) {
    for my $row ($worksheet->row_range()) {
        for my $col ($worksheet->col_range()) {
            my $cell = $worksheet->get_cell($row, $col);
            print $cell->value() if defined $cell;
        }
    }
}
```

### 注意事项

- 纯 Perl 模块，无 C/XS 组件，无需 CRT 文件 workaround
- conan-verify G4 检查（bin/lib/include）不适用于纯 Perl 模块
- 运行时需要 OLE::Storage_Lite 模块

---
*OpenHarmony 编译归档 · 2026-07-01*
