# TTMath (ttmath)

## 是什么

TTMath 是一个 header-only 的 C++ 模板大数库，提供大无符号整数、大有符号整数与大浮点数的基本算术运算，并附带一个数学表达式解析器。它完全以 C++ 模板编写，无需预先编译，消费者只需 `#include <ttmath/ttmath.h>` 即可使用。

## 功能概述

- `UInt<>`：大无符号整数（模板参数为机器字个数）
- `Int<>`：大有符号整数
- `Big<>`：大浮点数（可配置指数/尾数字长）
- `Parser<>`：数学表达式解析器
- 全部以模板实现，值的大小在编译期确定，无运行时分配

## OHOS 适配

- 纯 header-only，无构建产物，仅打包头文件到 `include/ttmath/`。
- OHOS aarch64（clang）下 ttmath 0.9.3 自动选择 `TTMATH_PLATFORM32` + `TTMATH_NOASM` 可移植实现（`ttmathuint_noasm.h`），无需任何源码补丁。
- 官方 0.9.3 发布包不含 `tests/`，官方测试套件位于同一 0.9.3 git tag 的 `tests/`，已原样 vendored 到本版本配方的 `upstream_tests/` 并在 `build()` 中编译运行。

## 依赖关系

- 编译/运行依赖：无（仅需 C++ 标准库 / libstdc++ 或 libc++，由工具链提供）。

## 参考资料

- 官网：https://www.ttmath.org/
- 源码仓：https://gitea.ttmath.org/tomasz.sowa/ttmath
- 发布包：https://downloads.sourceforge.net/project/ttmath/ttmath/ttmath-0.9.3/ttmath-0.9.3-src.tar.gz
