# any-lite 0.3.0 — Bootstrap 笔记（pc3-31）

## 来源核验（bootstrap 阶段，官方资料确认）
- 官方仓库：https://github.com/martinmoene/any-lite （GitHub 跳转到 nonstd-lite/any-lite 组织）
- 正式标签：`v0.3.0` → commit `8f7c53c605cc51d067a16c06054a7a4c23945a10`
- Release 发布时间：2020-11-28T08:21:12Z
- 许可证：Boost Software License 1.0（BSL-1.0）
- 源码 tarball：`https://github.com/martinmoene/any-lite/archive/refs/tags/v0.3.0.tar.gz`
- SHA-256：`fa7087ef7b4455c00b4b715649eb7176d6d0806c3a57cd4734845611ebe9888e`

## 结构
- 单文件头文件库：`include/nonstd/any.hpp`
- CMake INTERFACE library：目标 `nonstd::any-lite`，包 `any-lite`
- CMake 选项：`ANY_LITE_OPT_BUILD_TESTS` / `ANY_LITE_OPT_BUILD_EXAMPLES` / `ANY_LITE_OPT_SELECT_STD` / `ANY_LITE_OPT_SELECT_NONSTD`
- 上游自带 Conan 1.x 配方（`from conans import ...`）；本归档按 Conan 2.x 重写（optional-lite 同款模式）
- 上游测试使用 lest 框架：`test/any.t.cpp`

## 依赖
- 无任何第三方依赖（仅标准库）

## 首轮 Adapt / 本地验证
- 待执行：clang++ 编译 test_package smoke test + 上游 CTest 测试套件
