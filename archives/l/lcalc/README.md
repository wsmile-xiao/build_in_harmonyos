# lcalc

**lcalc — L 函数计算库与命令行工具 — 零点、特殊值、Riemann zeta 与一般 L 函数**

## 命令行工具

- `lcalc`

## 库

- `libLfunction.so`

## 构建

- 构建系统：autotools
- 许可证：GPL-2.0-or-later
- 上游：https://gitlab.com/sagemath/lcalc

## 依赖

- `pari/2.17.4`
- `gengetopt/2.23`

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 2.1.1 | built | 首个鸿蒙 PC conan 配方 |

## 为什么做这个包

passagemath（SageMath 的模块化重打包）在鸿蒙 PC 上的 wheel 需要它作为原生底座。
