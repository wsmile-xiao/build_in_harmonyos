# gcem (GCE-Math)

**Generalized Constant Expression Math** — 一个使用广义常量表达式的 C++ 编译期数学库。

- **版本**: 1.16.0
- **类型**: header-only（C++11 constexpr，兼容 C++11/14/17/20）
- **上游仓库**: https://github.com/kthohr/gcem
- **许可证**: Apache-2.0
- **依赖**: 无（仅需 C++11 兼容编译器）

## 适配要点

- gcem 是 header-only 库，`conanfile.py` 的 `package_type` 为 `header-library`，
  无编译步骤，仅拷贝 `include/` 头文件到包目录即可。
- 语法与 C++ 标准库一致（`gcem::sqrt`、`gcem::abs` 等），编译期可计算，
  数值精度经上游测试与标准库对齐。
- OHOS PC 平台无需额外适配（无平台相关代码、无系统调用）。

## 测试

- test_package 内以常量表达式断言验证 `gcem::` 接口在编译期与运行期均可用。