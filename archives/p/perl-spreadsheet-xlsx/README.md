# perl-spreadsheet-xlsx

Perl extension for reading MS Excel 2007 (.xlsx) files.

## 软件信息

- **官网**: https://metacpan.org/dist/Spreadsheet-XLSX
- **源码**: https://github.com/asb-capfan/Spreadsheet-XLSX
- **许可证**: perl_5 (Artistic License)
- **分类**: perl

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.18 | published | 2026-07-01 | 纯 Perl 模块，编译成功，conan-verify 全部通过，功能测试通过 |

## 运行依赖

- perl
- Archive::Zip (>= 1.18)
- Spreadsheet::ParseExcel
  - OLE::Storage_Lite (>= 0.19)
  - Crypt::RC4
  - Digest::Perl::MD5
  - IO::Scalar (IO::Stringy)

## 编译依赖

- perl (ExtUtils::MakeMaker)

## 使用说明

Spreadsheet::XLSX 是一个纯 Perl 模块，用于读取 Microsoft Excel 2007 (.xlsx) 文件。
它基于 Spreadsheet::ParseExcel 解析引擎，通过 Archive::Zip 解压 xlsx 文件。

### 安装

通过 Conan 安装：
```bash
conan install --requires=perl-spreadsheet-xlsx/0.18
```

安装后，设置 PERL5LIB 环境变量指向模块路径：
```bash
export PERL5LIB="<conan_package_path>/lib/perl5:$PERL5LIB"
```

### 示例

```perl
use Spreadsheet::XLSX;

my $excel = Spreadsheet::XLSX->new('file.xlsx');

foreach my $sheet (@{$excel->{Worksheet}}) {
    print "Sheet: " . $sheet->{Name} . "\n";
    for my $r ($sheet->{MinRow} .. $sheet->{MaxRow}) {
        for my $c ($sheet->{MinCol} .. $sheet->{MaxCol}) {
            my $cell = $sheet->{Cells}[$r][$c];
            print $cell->{Val}, "\t" if $cell;
        }
        print "\n";
    }
}
```

### 注意事项

- 此模块为纯 Perl 实现，无 C 扩展，无需特殊链接参数
- 运行时依赖通过 PERL5LIB 环境变量解析，不通过 Conan 依赖链管理
- 需确保所有运行时依赖模块（含间接依赖）已安装

---
*OpenHarmony 编译归档 · 2026-07-03*
