# OHOS libcxx-ohos std::ranges 算法缺失（all_of/any_of/equal）

> 草稿（B 类知识库贡献候选，随 clang20-ccache 20.1.8 PR 交付）。
> 关联任务：clang20-ccache-20.1.8-r01-pc3-7-20260921T084618Z
> similar_to: DRAFT-332-openrct2-0.5.3-libcpp15-cpp20-compat（同族 fill/lower_bound），
> DRAFT-clang18-ccache-18.1.8-ohos-libcxx-ranges-algorithms（ccache 族 4 文件实证链）

## 错误现场（本轮真实日志，cwd=/data/storage/el2/base/haps/entry/files/ccb-clang20-build）

```
src/ccache/config.cpp:93:15: error: reference to local variable 'prefix' declared in enclosing lambda expression
src/ccache/argprocessing.cpp:198:23: error: no member named 'all_of' in namespace 'std::ranges'
src/ccache/util/path.cpp:45:22: error: no member named 'all_of' in namespace 'std::ranges'
unittest/test_util_tokenizer.cpp:36:30: error: no member named 'equal' in namespace 'std::ranges'
```
命令: `cmake --build build -j4`（clang 15.0.4 aarch64-unknown-linux-ohos，CMAKE_CXX_STANDARD=20）
退出码: 2（首错 4 errors generated 后停止）

## 根因 / 适用范围
- 根因: OHOS SDK libcxx-ohos（LLVM 15.0.4, _LIBCPP_VERSION 15004）的 <ranges> 头存在，
  但 ranges 算法（all_of/any_of/equal 等）未实现，即使 -std=c++20 也缺失。
- 适用范围: 所有在 OHOS 上以 C++20 使用 std::ranges 算法的三方库（ccache、openrct2 等）；
  LLVM 16+ libc++ / libstdc++ 不受影响。
- 与 DRAFT-332 的关系: DRAFT-332（openrct2 0.5.3）覆盖 fill/lower_bound 缺失；
  本条补充 all_of/any_of/equal 三算法的具体替换模式与 ccache 4 文件实证链。

## 修复方案（已实测）
0001-src-ccache-argprocessing.cpp.patch:
```
-  return std::ranges::all_of(
-    util::Tokenizer(options, ",", util::Tokenizer::Mode::include_empty),
-    is_macro_option);
+  const auto tokens = util::Tokenizer(
+    options, ",", util::Tokenizer::Mode::include_empty);
+  return std::all_of(tokens.begin(), tokens.end(), is_macro_option);
```
0002-src-ccache-config.cpp.patch: `std::ranges::any_of(safe_dirs, ...)`
  → `std::any_of(safe_dirs.begin(), safe_dirs.end(), ...)`
0003-src-ccache-util-path.cpp.patch: `std::ranges::all_of(string, ...)`
  → `std::all_of(string.begin(), string.end(), ...)`
0004-unittest-test_util_tokenizer.cpp.patch: `std::ranges::equal(Tokenizer(...), expected)`
  → `const auto tokens = ...; std::equal(tokens.begin(), tokens.end(), expected.begin(), expected.end())`

要点: Tokenizer 等返回临时范围的场景，不能在同一表达式中对右值调用 begin()/end()，
需先绑定 const 局部变量再展开迭代器。

## 验证
- conan create（ohos-aarch64 profile）: exit 0，产物 bin/ccache 可执行
- ccache --version: "ccache version 4.14" 运行成功
- unittest: 243 例 | 240 通过 | 3 失败（HMDFS 硬链接平台限制，E079 家族）| 5 跳过（AVX2/路径条件）
- 消费者用例: ccache 包装 clang 编译 OHOS aarch64 hello.c，二次编译缓存命中（50% Hits），
  产物 ELF64 AArch64 运行输出 "hello from ccache consumer" 正确