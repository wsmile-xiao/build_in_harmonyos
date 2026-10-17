# OHOS libcxx-ohos std::ranges 算法缺失（all_of/any_of/equal）

> 草稿（B 类知识库贡献候选，随 clang22-ccache 22.1.8 PR 交付）。
> 关联任务：clang22-ccache-22.1.8-r03-pc3-9-20260922T051543Z
> similar_to: DRAFT-332-openrct2-0.5.3-libcpp15-cpp20-compat（同族 fill/lower_bound），
> DRAFT-graaf-1.1.0-ohos-libcxx-std-ranges-missing（同根因、headless 算法族），
> DRAFT-clang18-ccache-18.1.8-ohos-libcxx-ranges-algorithms（同族 ccache 实证）

## 错误现场（本轮真实日志，cwd=build-ohos，补丁应用前等价复现）

```
src/ccache/config.cpp:87:23: error: no member named 'any_of' in namespace 'std::ranges'
src/ccache/argprocessing.cpp:198:23: error: no member named 'all_of' in namespace 'std::ranges'
src/ccache/util/path.cpp:45:22: error: no member named 'all_of' in namespace 'std::ranges'
unittest/test_util_tokenizer.cpp:36:30: error: no member named 'equal' in namespace 'std::ranges'
```
命令: `cmake --build build-ohos -j4`（clang 15.0.4 aarch64-unknown-linux-ohos，CMAKE_CXX_STANDARD=20）
退出码: 2（首错 4 errors generated 后停止）
同族先例 clang18/20/21-ccache 相同 4 处错误签名与补丁内容完全一致（SHA-256 交叉核验一致）。

## 根因 / 适用范围
- 根因: OHOS SDK libcxx-ohos（LLVM 15.0.4, _LIBCPP_VERSION 15004）的 <ranges> 头存在，
  但 ranges 算法层（all_of/any_of/equal 等）未实现，即使 -std=c++20 也缺失。
- 适用范围: 使用 C++20 <ranges> 算法的三方库；ccache v4.14 命中
  argprocessing.cpp / config.cpp / util/path.cpp / unittest/test_util_tokenizer.cpp。
- 不受影响: LLVM 16+ libc++ / libstdc++。

## 修复（本轮 4 补丁已验证）
1. 0001-src-ccache-argprocessing.cpp.patch: `std::ranges::all_of(tokenizer, pred)` →
   `std::all_of(tokens.begin(), tokens.end(), pred)`（先绑定 const 局部 tokens）。
2. 0002-src-ccache-config.cpp.patch: `std::ranges::any_of(safe_dirs, pred)` →
   `std::any_of(safe_dirs.begin(), safe_dirs.end(), pred)`。
3. 0003-src-ccache-util-path.cpp.patch: `std::ranges::all_of(string, pred)` →
   `std::all_of(string.begin(), string.end(), ...)`。
4. 0004-unittest-test_util_tokenizer.cpp.patch: `std::ranges::equal(Tokenizer(...), expected)` →
   `std::equal(tokens.begin(), tokens.end(), expected.begin(), expected.end())`。

验证: 补丁应用后 conan create (ohos-aarch64) exit 0；test_package CONSUMER_PASS；
unittest 243 例 238 通过 5 失败（全为 HMDFS hardlink/fifo/fallocate 平台限制）5 跳过。

## 与既有知识的关系（七轴）
- exact_duplicate: false（无同 id 条目；同族 DRAFT 在各自 ccache 分支，未入 main）
- causal_duplicate: true（同根因 libc++15 <ranges> 不完整族，similar_to 明确）
- trigger_overlap: true（all_of/any_of/equal 与 DRAFT-332/E130 同族）
- solution_overlap: true（source-patch 迭代器替换，同 DRAFT-graaf/同族先例）
- combination_novelty: 低（无新组合）
- boundary_novelty: 低中（ccache 4 文件范围与同族一致，无新边界）
- test_migration_novelty: 低（unittest 1 处 ranges::equal 迁移，同族先例已覆盖）

路径判断: 同族先例（clang18/20/21-ccache）均以 new_draft 交付同 stem 草稿；
本库按同族 pattern 建立 new_draft（.kv/.md 配对），随 clang22-ccache PR 交付。