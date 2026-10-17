# E999 — OHOS libc++ (libcxx-ohos) 缺 C++20 std::ranges::all_of/any_of/equal 的迭代器版替换

> Status: Draft | Contributor: AtomCode/oh-executor (23FF) | Updated: 2026-09-21
> Source: clang21-ccache 21.1.8（ccache v4.14 源码，CMake C++20，CLI 工具包）
> 对应：knowledge/drafts/E999-draft-23FF.kv

## 错误特征

OHOS SDK clang 15.0.4（libcxx-ohos，LLVM 15）下以 `-std=c++20` 编译 ccache v4.14，
凡使用 `std::ranges` 算法的编译单元报错：

```text
error: no member named 'all_of' in namespace 'std::ranges'
error: no member named 'any_of' in namespace 'std::ranges'
error: no member named 'equal' in namespace 'std::ranges'
```

命中位置：`src/ccache/argprocessing.cpp`（all_of）、`src/ccache/config.cpp`（any_of）、
`src/ccache/util/path.cpp`（all_of）、`unittest/test_util_tokenizer.cpp`（equal）。

## 触发条件

- 构建系统: CMake（project(ccache LANGUAGES C CXX)，C++20 必需）
- 阶段: compilation（含上游 unittest 测试目标）
- 工具链: OHOS SDK 26.0.0.18 / clang 15.0.4 / libcxx-ohos

## 根因分析

OHOS PC SDK 自带 libcxx-ohos（LLVM 15 基线）未实现 `<ranges>` 的算法层：
`std::ranges::all_of / any_of / equal` 等均不存在，只有概念与范围基础件。
上游在标准 libc++（Linux）上编译正常，OHOS 工具链直接报
"no member named 'xxx' in namespace 'std::ranges'"。属工具链能力缺口
（与 E130 的 nullptr_t/__abi_tag__ 同源不同面），经典迭代器算法在
libcxx-ohos 完整可用，可安全等价替换。

## 解决方案

### 推荐方案（source-patch，本条目验证）

4 个最小补丁将 `std::ranges::` 调用替换为迭代器版 `std::` 算法：

```cpp
// 原: std::ranges::all_of(util::Tokenizer(options, ",", include_empty), is_macro_option)
// 改:
const auto tokens = util::Tokenizer(options, ",", util::Tokenizer::Mode::include_empty);
return std::all_of(tokens.begin(), tokens.end(), is_macro_option);

// 原: std::ranges::any_of(safe_dirs, [&](const auto& safe_dir) {...})
// 改: std::any_of(safe_dirs.begin(), safe_dirs.end(), [&](const auto& safe_dir) {...})

// 原: std::ranges::equal(util::Tokenizer("a,b,c", ","), expected)
// 改:
const auto tokens = util::Tokenizer("a,b,c", ",");
CHECK(std::equal(tokens.begin(), tokens.end(), expected.begin(), expected.end()));
```

**关键边界（CLI 工具包新增差异）**：上游测试源（unittest/test_util_tokenizer.cpp 的
`ranges::equal`）必须**一并替换**，否则 `unittest` 测试目标编译失败；既有 graaf 草稿
仅覆盖生产源（max_element/min_element/count_if），未覆盖测试源同步替换。

### 禁止做法

- ❌ 抬升 `-std=c++2b/-std=c++23` 绕过：引入 C++23 编译面，不解决测试源真实编译
- ❌ 只压制诊断不改代码：等于伪造编译结论

## 验证

```bash
# conan create（OHOS aarch64 profile）全绿
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# ccache --version → "ccache version 4.14"

# 上游 unittest 全量（合格挂载点 TMPDIR 指向 0700 目录）
./unittest/unittest
# [doctest] test cases: 243 | 240 passed | 3 failed | 5 skipped
# （3 例失败均为 HMDFS 硬链接平台限制，E079 家族，与 ranges 无关）
```

## 关联条目

- similar_to: DRAFT-graaf-1.1.0-ohos-libcxx-std-ranges-missing（max_element/min_element/count_if 同方案族）、DRAFT-ohos-libcxx15-missing-cpp20-ranges-algorithms（ada polyfill 方案）、DRAFT-icecream-cpp-1.0.0-cpp20-ranges-toolchain-gap（std::views 缺失，阻塞归类）
- caused_by: E130（libcxx-ohos 能力缺口同源）