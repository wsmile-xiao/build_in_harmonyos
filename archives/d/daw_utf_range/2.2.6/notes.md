# daw_utf_range 2.2.6 适配笔记

## 编译环境
- 构建系统: cmake（header-only CMake INTERFACE library）
- 编译日期: 2026-09-22
- 编译器: clang/clang++ 15.0.4（OHOS aarch64，/data/service/hnp/bin）
- 状态: built

## 背景与动机

积分赛任务绑定库名 `daw_utf_range`（下划线命名），对应上游 beached/utf_range v2.2.6。
本仓库 main 已存在同源连字符命名归档 `archives/d/daw-utf-range/2.2.6`
（【依赖项】PR a43244a4，2026-09-19，制品仓已发布 daw-utf-range/2.2.6）；
本任务按任务正文 `lib: daw_utf_range` 绑定与 `delivery_allowed_paths` 约束，
在下划线命名目录独立完成适配与直接 PR 交付，不触碰既有连字符归档。

制品仓核验（2026-09-22 实测）：
- `conan download daw-header-libraries/2.135.0 -r=ohpcd --only-recipe` → 已发布 ✅
- `conan download daw-utf-range/2.2.6 -r=ohpcd --only-recipe` → 已发布（既有连字符包，仅作参考）

## 编译步骤

```bash
# 源码: beached/utf_range v2.2.6（官方 tag，SHA-256 314e12d3...）
# 配方验证（OHOS aarch64 profile）
conan create archives/d/daw_utf_range/2.2.6 \
  -pr:h ci/conan/profiles/ohos-aarch64 -pr:b default --build=missing
# → conan create PASS，test_package 消费者测试 PASS（5 断言全覆盖）

# W3 本地 CI 模拟（ohc-run.py finish 内嵌，超时预算 3600s）
# → setup.sh PASS + build_and_test.sh PASS（JC/L0-L5 全绿）

# 上游测试构建与运行（DAW_ENABLE_TESTING=ON + DAW_USE_PACKAGE_MANAGEMENT=ON，
# 依赖头由 conan install daw-header-libraries/2.135.0 提供，不联网 FetchContent）
cmake -S . -B build-tests -DDAW_ENABLE_TESTING=ON -DDAW_USE_PACKAGE_MANAGEMENT=ON \
  -DCMAKE_TOOLCHAIN_FILE=<daw-hl>/conan_toolchain.cmake -DCMAKE_PREFIX_PATH=<daw-hl>
cmake --build build-tests -j2
ctest --test-dir build-tests --output-on-failure
# → 2/2 注册项 PASS（见「验证结果」节）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 默认构建走 FetchContent 拉依赖 | extern/CMakeLists.txt 声明 FetchContent(daw_header_libraries) | CMakeToolchain 注入 `DAW_USE_PACKAGE_MANAGEMENT=True`，改走 find_package（依赖由 Conan CMakeDeps 提供） |
| 2 | 上游 daw_utf_string 的 add_test COMMAND 写成 daw_utf_range（上游笔误） | tests/CMakeLists.txt `add_test(NAME daw_utf_string_test COMMAND daw_utf_range)` | 上游原样保留不修；ctest 2/2 注册项按上游语义通过，另直跑 daw_utf_string 二进制记录真实行为 |
| 3 | 上游 utf_string_sort_001/002 断言失败（size 21→42 翻倍） | 上游 `utf_string::sort()` 缺陷：`to_u32string()` 已含全部码点后又 `std::copy(cbegin(), cend(), back_inserter(result))` 重复追加 | 非适配问题（上游代码缺陷），不修补丁——直跑实测复现（exit=134 / expected_failure），消费者测试不覆盖 sort 路径，豁免记录于此 |
| 4 | W3 本地 CI 模拟 JC 整仓扫描误拦 | junk_check full 模式（无 origin/main 时回退）扫到**其他库**已合入 main 的基线空标记文件（cloog 0.21.1 / kics 2.1.20 的 .build-closed/.staging-verified，blob e69de29…，不在本任务允许路径内） | 按「无关历史基线」处理：不改动基线文件，用 JUNK_PR_DIFF（仅含本库 8 个提交文件）切 prdiff 模式复验，JC/L0-L5 通过；隔离/恢复审计见最终报告 |
| 5 | ohc-run gen_summary 报 `'str' object has no attribute 'append'` | 工具内部 bug（SUMMARY.md 属框架文件，本任务不提交） | 不修复框架、不提交 SUMMARY.md，如实记录 |

## 源码修改

无需补丁（header-only 库，无平台适配代码修改）。

## 依赖版本

- daw-header-libraries/2.135.0（制品仓已发布）

## 验证结果

```bash
# conan create + test_package（消费者测试）
# → PASS: daw_utf_range header-only 库链接和核心 API 验证通过
#   覆盖: create_char_range 多文种码点遍历 / utf_string 比较+构造 /
#         utf8::unchecked 迭代（daw_json_link 序列化同款头），5 断言全过

# 上游 ctest（DAW_ENABLE_TESTING=ON，OHOS SDK libc++ 运行时）
# → daw_utf_range_test: PASS（char_range 多文种遍历）
# → daw_utf_string_test 注册项: PASS（上游 add_test 笔误实跑 daw_utf_range）
# → daw_utf_string 直跑: exit=134，复现上游 sort() 缺陷（豁免，见问题表 #3）
# → 实测口径: ctest 2/2 注册项全过；daw_utf_string 4 测试函数中 2 过 2 豁免
```

## 注意事项

- header-only 库（6 个头文件），package_type = header-library，cpp_info.libs 为空。
- CMake 目标: daw::daw-utf-range（install EXPORT NAMESPACE daw::）；配方包名 daw_utf_range，cmake_file_name 保持 daw-utf-range 与上游安装配置一致。
- OHOS 适配: generate() 中 os in ("Linux","OHOS") 时注入 CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64（R32）。
- 知识判定: 快照扫描无等价命中（E342 为邻近但根因/方案不同），本库同版本既有归档已完整记录同一方案 → path_a_no_knowledge，路径 A，不创建草稿。

---

**编译结束**: 2026-09-22
**最终状态**: built
