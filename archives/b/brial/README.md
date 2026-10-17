# brial

**BRiAl — 布尔环代数框架（PolyBoRi 的后继）— 布尔多项式环上的 Gröbner 基与化简**

## 库

- `libbrial.so`
- `libbrial_groebner.so`

## 构建

- 构建系统：autotools
- 许可证：GPL-2.0-or-later
- 上游：https://github.com/BRiAl/BRiAl

## 依赖

- `boost/1.91.0.1`
- `m4ri/20260122`
- `libpng/1.6.58.1(force)`

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 1.2.15 | built | 首个鸿蒙 PC conan 配方 |

## 为什么做这个包

passagemath（SageMath 的模块化重打包）在鸿蒙 PC 上的 wheel 需要它作为原生底座。
