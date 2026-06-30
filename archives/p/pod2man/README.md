# pod2man (podlators)

pod2man 是 Perl 文档生成工具，用于将 POD（Plain Old Documentation）格式转换为 nroff/troff 格式，适用于 man pages。

## 版本信息
- 当前版本: 6.0.2
- 发布日期: 2024-07-15
- 官网: https://www.eyrie.org/~eagle/software/podlators/

## 描述
podlators 包含 Pod::Man 和 Pod::Text 模块，用于将 POD 输入转换为：
- *roff source output（适用于 man pages）
- plain text（纯文本格式）

主要功能：
- pod2man: 将 POD 转换为 man page 格式
- pod2text: 将 POD 转换为纯文本格式
- Pod::Man: Perl 模块，生成 nroff/troff 源码
- Pod::Text: Perl 模块，生成纯文本

## 编译状态
- 鸿蒙难度: 🟢 (简单)
- 构建系统: ExtUtils::MakeMaker (Perl)
- 编译器: Perl 5.42.0

## 依赖
- Perl 5.12 或更高版本
- Pod::Simple 3.26 或更高版本（Perl 5.17.10 已包含）

## 使用方式
```bash
# 将 POD 文件转换为 man page
pod2man input.pod output.1

# 将 POD 文件转换为纯文本
pod2text input.pod output.txt

# 在 Perl 程序中使用
use Pod::Man;
my $parser = Pod::Man->new();
$parser->parse_from_file('input.pod', 'output.1');
```

## 已知问题
- pod2man 和 pod2text 是 Perl 脚本，不是编译的二进制文件
- 使用 ExtUtils::MakeMaker 构建系统，不是标准的 autotools

## License
Artistic-1.0-Perl OR GPL-1.0-or-later