# eclib

**eclib (mwrank) — 有理数域上椭圆曲线的算术 — 导子/Tate 算法、mwrank 求 Mordell-Weil 秩、模符号**

## 库

- `libec.so`

## 构建

- 构建系统：autotools
- 许可证：GPL-2.0-or-later
- 上游：https://github.com/JohnCremona/eclib

## 依赖

- `pari/2.17.4`
- `ntl/11.6.0.2`
- `flint/3.6.0`
- `gmp/6.3.0.1(force)`

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 20250627 | built | 首个鸿蒙 PC conan 配方 |

## 为什么做这个包

passagemath（SageMath 的模块化重打包）在鸿蒙 PC 上的 wheel 需要它作为原生底座。
