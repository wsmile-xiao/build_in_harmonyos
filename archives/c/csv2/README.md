# csv2

Fast, header-only C++ library for parsing/writing CSV data.

- 上游: https://github.com/p-ranav/csv2
- 版本: 0.1 (tag v0.1, commit a20992f7a1b75215609037c4cc66f690e8691aab)
- 许可证: MIT

## OHOS 适配

- **构建系统**: CMake（INTERFACE header-only 库，C++11）
- **依赖链**: 无第三方依赖
- **编译**: 使用 OHOS 社区 clang 15（aarch64-unknown-linux-ohos）与 CMake 直接编译；
  `generate()` 内按 R32 将 OHOS 映射为 `CMAKE_SYSTEM_NAME=Linux` + `aarch64`
- **测试**: 上游 doctest 19 用例 / 161 断言全绿；附 OHOS 专项测试
  （`ohos_csv2_test`：Reader mmap/表头/引号转义/trim + Writer 文件输出）

## 版本

| 版本 | 目录 | 状态 |
|------|------|------|
| 0.1 | [0.1/](0.1/) | built |