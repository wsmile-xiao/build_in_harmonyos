# fplll

**fplll — 格基约化库与命令行工具 — LLL / BKZ / HKZ 约化与 SVP、CVP 求解**

## 命令行工具

- `fplll`
- `latticegen`

## 库

- `libfplll.so`

## 构建

- 构建系统：autotools
- 许可证：LGPL-2.1-or-later
- 上游：https://github.com/fplll/fplll

## 依赖

- `gmp/6.3.0`
- `mpfr/4.2.2.1`

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 5.5.0 | built | 首个鸿蒙 PC conan 配方 |

## 为什么做这个包

passagemath（SageMath 的模块化重打包）在鸿蒙 PC 上的 wheel 需要它作为原生底座。
