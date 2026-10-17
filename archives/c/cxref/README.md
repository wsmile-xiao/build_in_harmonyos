# cxref

`cxref` 是 Andrew M. Bishop 编写的 C 交叉引用与文档工具。它解析 C 源码（自带词法/语法分析器，
并内嵌 cxref-cpp 预处理器），提取文件、函数、变量、类型、`#include` 等信息，生成 LaTeX、HTML、
RTF、SGML 格式的交叉引用文档，并可用 `cxref-query` 查询生成的原始数据库。

- 上游仓库：https://www.gedanken.org.uk/software/cxref/
- 许可证：GPL-2.0-or-later
- 构建系统：autoconf-2.13 时代 configure + 手写 Makefile.in（src/ cpp/ query/ doc/ 四个子目录）
- 类型：命令行工具（安装 bin/ 下 cxref、cxref-cc、cxref-cpp、cxref-cpp-configure、cxref-query）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.6e | built | 首次适配 HarmonyOS PC (aarch64)；configure/cpp-configure umask 022 修正 + 包内自洽 prefix |
