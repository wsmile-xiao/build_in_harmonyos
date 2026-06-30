# inih (INI Not Invented Here)

inih 是一个简单的 C 语言 INI 文件解析器。它只有几页代码，设计为小型且简单，适合嵌入式系统。它与 Python 的 ConfigParser 风格的 .INI 文件基本兼容，包括 RFC 822 风格的多行语法和 `name: value` 条目。

## 特性

- SAX 风格解析（回调函数）
- 支持多行条目
- 支持 UTF-8 BOM
- 支持内联注释
- 低内存占用
- 适合嵌入式系统

## 官方地址

- GitHub: https://github.com/benhoyt/inih
- License: BSD-3-Clause