# coordgenlibs

Schrödinger 开源的 2D 分子坐标生成库（sketcher minimizer）。输入分子拓扑（原子、键、键序、环），输出版面美观的 2D 坐标；内置环模板库（苯环、稠环、大环等）。RDKit 的 `CoordGen` 坐标生成集成的上游。

- 上游：https://github.com/schrodinger/coordgenlibs
- 许可证：BSD-3-Clause
- 语言/构建：C++11 / CMake（`project(coordgen)`）

## 依赖

- 库本体零依赖（上游默认 `COORDGEN_USE_MAEPARSER=OFF`，模板数据编译期内嵌）。
- 可选：maeparser（运行时读取 `.mae` 模板文件；本包按上游默认不启用）。

## OHOS 适配要点

- 上游 CMakeLists 固定 `CMAKE_CXX_STANDARD 11`（低于 profile `cppstd=17`），按上游显式选择编译。
- 上游 `cmake_minimum_required(3.2)` 在 CMake 4.x 下需 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。
- `COORDGEN_RIGOROUS_BUILD=ON`（`-Wall -Wextra -Werror`）下库本体在 OHOS clang 15 零告警通过。
- 上游测试：Boost.Test 实现（`libboost_unit_test_framework`）在仓库 boost 包中无预编译产物，测试侧以官方 `BOOST_TEST_SOURCE` 手动静态编译模式（`boost/test/impl/*.ipp`）补齐。

## 已适配版本

- 3.0.2（status: built）
