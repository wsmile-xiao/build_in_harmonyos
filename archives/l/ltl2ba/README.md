# ltl2ba

ltl2ba (LTL2BA) 是线性时序逻辑 (LTL) 到 Büchi 自动机的快速翻译器，基于 Gastin 与 Oddoux 在 CAV 2001 发表的算法。它将一个 LTL 公式翻译为 Spin 模型检查器可用的 never claim（即 Büchi 自动机）。

## 功能概述

- 将 LTL 公式翻译为 Büchi 自动机（Spin never claim 格式）
- 支持时序算子：`[]`（always/G）、`<>`（eventually/F）、`U`（until）、`V`（release/R）、`X`（next）
- 支持布尔算子：`!`、`&&`、`||`、`->`、`<->`
- 在线与后置自动机化简，状态数少、内存占用低

## OHOS 适配要点

- **构建系统**: 简单 Makefile（无 CMake、无 autotools `configure`），在 conanfile.py 的 `build()` 中覆盖 `CC`/`CFLAGS` 即可交叉编译
- **解析器/词法器**: `parse.c`/`lex.c` 为手写 C 源码（非 flex/bison 生成产物），无需额外工具链
- **依赖**: 仅依赖标准 POSIX 头文件（stdio/stdlib/string/unistd/sys/time/sys/resource），无 Linux 专属假设，零 patch
- **产物**: 单一可执行文件 `ltl2ba`，安装到 `package/bin`（命令行工具，非库）
- **许可证**: GPL-2.0-or-later（源码附 LICENSE 文件）
- **测试**: 无上游测试套件；test_package 运行三个典型 LTL 公式并校验 Büchi 自动机输出

## 使用示例

```bash
# always p
ltl2ba -f "[]p"

# eventually p
ltl2ba -f "<>p"

# p until q
ltl2ba -f "p U q"

# 从单行文件读取公式
ltl2ba -F formula.txt
```

## 版本

- **1.3**（June 2020）：Paul Gastin 修订版，由 Jerry James 贡献的 bug 修复
