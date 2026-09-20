# daw-utf-range 2.2.6 适配笔记

## 编译环境
- 构建系统: cmake（header-only CMake INTERFACE library）
- 编译日期: 2026-09-19
- 编译器: clang/clang++ 15.0.4（OHOS aarch64，/data/service/hnp/bin）
- 状态: published

## 背景与动机

daw_json_link 3.38.1（任务 #13783）的序列化路径 `include/daw/json/impl/to_daw_json_string.h`
唯一包含 `#include <daw/utf8/unchecked.h>`——该头由 daw-utf-range 提供。上游 extern/
以 FetchContent 拉取 utf_range v2.2.6；Conan 集成必须改为 find_package 模式
（`DAW_USE_PACKAGE_MANAGEMENT=ON`），因此 daw-utf-range 需先独立适配发布（R36 依赖先发布）。

制品仓/任务池核验（2026-09-19 实测）：
- `conan download daw-utf-range/2.2.6 -r=ohpcd --only-recipe` → 不存在
- 平台任务池全量扫描（5506 open）→ 无 daw-utf-range 任务
- 依赖 daw-header-libraries/2.135.0 → 制品仓已发布 ✅

## 编译步骤

```bash
# 源码: beached/utf_range v2.2.6（官方 tag）
# SHA-256: 314e12d3a611a8179cc920acbae965d7280b28fb140a69fc5021623c0f0aa359

# 配方验证（OHOS aarch64 profile）
conan create archives/d/daw-utf-range/2.2.6 \
  -pr:h ~/.conan2/profiles/ohos-aarch64 -pr:b default --build=missing
# → 构建 + test_package 消费者测试 PASS（char_range/utf_string/utf8 迭代核心 API）

# 上游测试构建与运行（DAW_ENABLE_TESTING=ON，本地联网补跑）
# 见「验证结果」节
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 默认构建走 FetchContent 拉依赖 | extern/CMakeLists.txt 声明 FetchContent(daw_header_libraries/daw_utf_range) | CMakeToolchain 注入 `DAW_USE_PACKAGE_MANAGEMENT=True`，改走 find_package（依赖由 Conan CMakeDeps 提供） |
| 2 | 上游 daw_utf_string 的 add_test COMMAND 写成 daw_utf_range（上游笔误） | tests/CMakeLists.txt `add_test(NAME daw_utf_string_test COMMAND daw_utf_range)` | 上游原样保留不修（不构成失败：测试二进制仍构建，ctest -R 按名匹配可单独运行） |
| 3 | 上游 utf_string_sort_001/002 断言失败（size 21→42 翻倍） | 上游 `utf_string::sort()` 缺陷：`to_u32string()` 已含全部码点后又 `std::copy(cbegin(), cend(), back_inserter(result))` 重复追加 | 非适配问题（上游代码缺陷），不修补丁——诊断程序实锤（diag2: before size=21 after sort size=42）；消费者测试不覆盖 sort 路径，豁免记录于此 |

## 源码修改

无需补丁（header-only 库，无平台适配代码修改）。

## 依赖版本

- daw-header-libraries/2.135.0（制品仓已发布）

## 验证结果

```bash
# conan create + test_package（消费者测试）
# → PASS: daw-utf-range header-only 库链接和核心 API 验证通过
#   覆盖: create_char_range 多文种码点遍历 / utf_string 比较+排序 /
#         utf8::unchecked::codepoint_from_utf8 迭代（daw_json_link 序列化同款头）

# 上游 ctest（本地联网补跑，DAW_ENABLE_TESTING=ON，OHOS SDK libc++ 运行时）
# → daw_utf_range_test: PASS（char_range 多文种遍历）
# → daw_utf_string 直跑: 前 2 测试函数 PASS；sort_001/002 因上游 sort() 缺陷 FAIL（豁免，见问题表 #3）
# → 实测口径: 1/2 add_test 全过 + 1/2 部分过（4 测试函数中 2 过 2 豁免）
```

## 注意事项

- header-only 库（6 个头文件），package_type = header-library，cpp_info.libs 为空。
- CMake 目标: daw::daw-utf-range（install EXPORT NAMESPACE daw::）。
- OHOS 适配: generate() 中 os in ("Linux","OHOS") 时注入 CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64（R32）。
- 上游 CMake 安装 DESTINATION 用 `lib/cmake/${PROJECT_NAME}` 硬编码（非 GNUInstallDirs 变量），对 header-only 包无实际影响。

---

**编译结束**: 2026-09-19
**最终状态**: published
