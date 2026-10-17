# cpp-sort

Sorting algorithms & related tools，header-only C++17 库，由 Morwenn 维护。

- 官方仓库：https://github.com/Morwenn/cpp-sort（上游 tag `v2.2.0`）
- 许可证：MIT
- 版本：2.2.0
- 适配说明：header-only（CMake INTERFACE library），打包 include/ 头文件与
  CMake 包配置（`cpp-sort::cpp-sort`），无任何第三方依赖。
- 目录结构：`archives/c/cpp-sort/{version}/`（conanfile.py + conandata.yml +
  test_package/ + manifest.yaml + notes.md + reports/）
- 验证：上游 Catch2 测试 1462/1462 通过；OHOS 专项测试通过；
  `conan create`（OHOS aarch64 profile）与 test_package 消费者验证通过。