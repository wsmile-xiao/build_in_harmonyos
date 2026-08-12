# GnuCOBOL

GnuCOBOL 是 GNU 项目的 COBOL 编译器套件，可将 COBOL 源码转换为 C 代码并生成本机可执行程序或动态模块。

## 上游信息

- 官网: https://www.gnu.org/software/gnucobol/
- 源码: https://sourceforge.net/projects/gnucobol/
- 编译器许可证: GPL-3.0-or-later
- 运行时库许可证: LGPL-3.0-or-later
- 构建系统: Autotools

## 已适配版本

- 3.2: OpenHarmony/HarmonyOS PC arm64，状态 `built`

## 命令

- `cobc`: COBOL 编译器
- `cobcrun`: COBOL 动态模块运行器
- `cob-config`: libcob 编译与链接参数查询工具

GnuCOBOL 3.2 依赖 GMP 6.3.0。发布顺序必须先 GMP、后 GnuCOBOL。
