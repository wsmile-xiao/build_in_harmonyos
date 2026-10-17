# verdict

Verdict 是一组用于计算 2D/3D 有限单元质量度量的 C++ 库，由 Sandia National Laboratories
（NTESS）开发，源自 CUBIT 网格质量工具箱。提供边、三角形、四边形、四面体、六面体、
楔形、金字塔与刀形单元的几何质量指标（面积/体积、Jacobian、skew、aspect ratio、
radius ratio、shape 等），以 `namespace verdict` 的形式导出公共 API（`verdict.h`）。

- 官网/仓库: https://github.com/sandialabs/verdict
- 许可证: BSD-3-Clause
- 构建系统: CMake

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 1.4.5 | built | 首次适配；上游 67 个 GoogleTest 用例在 OHOS aarch64 真机执行，test_package 10 项消费者断言 |
