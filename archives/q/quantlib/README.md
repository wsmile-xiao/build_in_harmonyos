# QuantLib

QuantLib 是开源量化金融计算库，提供收益率曲线、衍生品定价、风险模型、随机过程和数值方法等功能。

## 编译版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 1.43 | built | 2026-08-19 |

## 功能特点

- C++ 量化金融核心库
- 支持收益率曲线、期权定价、信用衍生品、固定收益等模块
- 使用 CMake 构建
- 依赖 Boost

## HarmonyOS PC 适配说明

- HarmonyOS 缺少 `pthread_setcancelstate`，Boost 1.84 需定义 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE=1`。
- Boost.Math 在 OHOS `long double` 路径上可能触发数值不收敛，需定义 `BOOST_MATH_PROMOTE_DOUBLE_POLICY=0`。
- 使用静态构建规避 OHOS 下 shared library 运行时符号解析问题。
