# z3

Z3 是微软研究院开发的高性能定理证明器（SMT solver）。它可以用于验证软件和硬件系统、解决约束问题、分析和优化逻辑公式等。

## 描述

Z3 是一个跨平台的定理证明器，支持多种逻辑理论：
- 线性算术（整数和实数）
- 非线性算术
- 位向量
- 数组
- 数据类型
- 字符串
- 浮点数
- 量词

## 版本信息

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 4.15.4 | built | 2026-05-20 |

## 构建特性

- **构建系统**: CMake（不支持 autotools）
- **编译器**: clang 15.0.4
- **平台**: HarmonyOS aarch64
- **共享库**: libz3.so
- **Python 绑定**: 未构建（避免依赖）
- **GMP 依赖**: 无（使用内部实现）

## 使用方法

```bash
# 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- z3 4.15.4

# 使用 z3
z3 --version
echo "(declare-const x Int) (assert (> x 100)) (check-sat)" | z3 -in
```

## API 使用

C++ API:
```cpp
#include "z3++.h"
using namespace z3;

context c;
expr x = c.int_const("x");
solver s(c);
s.add(x > 100);
std::cout << s.check() << std::endl;  // sat
```

## 注意事项

1. z3 的 Python 构建脚本（configure）不支持 HarmonyOS，必须使用 CMake。
2. 避免使用 `-DZ3_BUILD_PYTHON_BINDINGS=ON` 以减少 Python 依赖。
3. 使用 `-DZ3_USE_LIB_GMP=OFF` 避免 GMP 库依赖。
