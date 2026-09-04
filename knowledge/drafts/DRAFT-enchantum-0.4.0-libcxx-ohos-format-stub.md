# DRAFT：OHOS SDK libcxx-ohos 的 `<format>` 占位头

- **草稿 ID**: DRAFT-enchantum-0.4.0-libcxx-ohos-format-stub
- **来源库**: enchantum 0.4.0（任务 enchantum-0.4.0-r01-pc1-52）
- **判定**: 路径 B（知识库扩展候选，新增知识，无正式条目覆盖）

## 问题

OHOS SDK 26.0.0.18 自带的 clang15 标准库（libcxx-ohos）提供 `<format>` 头文件，
`__has_include(<format>)` 返回真；但该头只是占位实现——`std::format`、
`std::formatter`、`std::formatter<string_view>` 均未真正实现。以 `__has_include`
作守卫的上游测试（如 enchantum `tests/double_include.cpp` 中的
`#if __has_include(<format>)`）会误判放行，进而在包含 `std_format.hpp` 特化
`std::formatter` 时编译失败。

## 根因

- libcxx-ohos 提供占位 `<format>` 头，头存在 ≠ 功能可用；
- 上游 CMake 的 `check_cxx_source_compiles`（HAS_STD_FORMAT）能正确探测失败并
  剔除 `std_format.cpp`，但无法覆盖 `double_include.cpp` 的 `__has_include` 守卫路径；
- 首个错误：`std_format.hpp:9:13: error: explicit specialization of non-template struct 'formatter'`。

## 方案

判定 `<format>` 可用性必须用**编译探测**（CMake `check_cxx_source_compiles` 或
`clang++ -std=c++20 -fsyntax-only` 探针），禁止仅凭 `__has_include(<format>)` 放行。
库配方保持 C++17 最低版本（INTERFACE `cxx_std_17`）；C++20 专属测试由上游 CMake 的
`STD < 20` / `HAS_STD_FORMAT` 门自动剔除，无需源码补丁。

## 验证

- 编译探测：`cmake -DCMAKE_CXX_STANDARD=20` 配置输出 `HAS_STD_FORMAT - Failed`；
- C++20 构建首错：`std_format.hpp:9:13: explicit specialization of non-template struct 'formatter'`，
  命令 `cmake --build . --target tests`，cwd=`$HOME/tmp/enchantum-build-cxx20`，退出码 2；
- 规范配置（C++17）：上游测试 ctest 362/362 通过（100%）；OHOS aarch64 专项测试 PASS。

## 适用边界

- 适用：OHOS SDK 26.0.0.18 / clang15 / libcxx-ohos 工具链上所有依赖 C++20
  `<format>` 或使用 `__has_include(<format>)` 守卫的库；
- 不适用：工具链升级到完整实现 `<format>` 的 libc++（clang 16+ / GCC 13+）之后。

## 查重差异

- E130（libcxx-ohos 需 C++17 最低）键为 `nullptr_t`/`__abi_tag__` 与 C++11 标准，
  不覆盖 `<format>` 占位头/功能缺失；
- index.tsv / graph E*.kv / doc/ / drafts/ 四范围检索 `std::format`、
  `std::formatter`、`HAS_STD_FORMAT`、`__has_include` 均无同义条目。