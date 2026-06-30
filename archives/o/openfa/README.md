# openfa — Open Fundamental Astronomy

## 软件描述
OpenFA 是基于 SOFA（Standards of Fundamental Astronomy）库的 C 语言库实现。SOFA 库由国际天文联合会（IAU）维护，提供基础天文学标准模型和算法。

OpenFA 由 IMCCE（巴黎天文台天体力学与历表计算研究所）维护，采用 BSD-3 许可证，使其兼容更广泛的开源许可证。

## 版本
- 当前版本：20231011.0.3
- 版本规则：MAJOR.MINOR.PATCH
  - MAJOR = SOFA 版本日期（20231011 → 2023-10-11）
  - MINOR = SOFA 修订字母（0 = 初始, 1 = a, ...）
  - PATCH = OpenFA 修订号

## 构建信息
- 构建系统：CMake
- 语言：C
- 产物类型：静态库（libopenfa.a）
- 依赖：无外部依赖（仅 libc 数学库）

## 与 SOFA 的区别
- 函数前缀：`openfa` 替代 `iau_`（如 `openfaCal2jd` 替代 `iauCal2jd`）
- 宏前缀：`OPENFA_` 替代 `SOFA_`
- 许可证：BSD-3-Clause（替代 SOFA 的限制性许可证）

## 来源
- 官方网站：https://gitlab.obspm.fr/imcce_openfa/openfa
- 维护者：IMCCE, CNRS, Observatoire de Paris, PSL
