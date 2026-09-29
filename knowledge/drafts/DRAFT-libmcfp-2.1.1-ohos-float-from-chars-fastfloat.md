# DRAFT-libmcfp-2.1.1-ohos-float-from-chars-fastfloat

> 主题：OHOS libc++ 缺浮点 `std::from_chars`，上游用 CPM 从 github.com 拉
> fast_float 作回退 → 预装 ohpcd `fast_float/8.0.1` conan 包 + 补丁改
> `find_package(fast_float CONFIG QUIET)` 优先 + 目标名 `FastFloat::fast_float` →
> `fast_float::fast_float`。
> 来源：libmcfp 2.1.1 首轮适配（pc4-13）。状态：DRAFT（待主编审核转正式）。

## 现象 (Problem)

1. 编译探测程序 `cmake/test-charconv.cpp` 在 OHOS 工具链下失败：

```
error: call to deleted function 'from_chars'
  auto r = std::from_chars(s, s + strlen(s), v);
charconv: candidate function has been explicitly deleted
  from_chars_result from_chars(const char*, const char*, bool, int = 10) = delete;
note: candidate template ignored: requirement 'is_integral<float>::value' was not satisfied
```

2. 顶层 CMakeLists `try_compile(STD_CHARCONV_COMPILING, CXX_STANDARD 23)` 失败后走
   `CPMFindPackage(NAME FastFloat GIT_REPOSITORY https://github.com/fastfloat/fast_float GIT_TAG v8.0.2)`，
   在 configure 期尝试从 github.com 下载 fast_float —— 网络受限 worker 上直接失败：

```
CMake step for fastfloat failed: 1
  (FetchContent … git … GIT_VERSION_STRING='' … network)
```

## 根因 (Root Cause)

- OHOS SDK 26.0.0.18 的 libcxx-ohos `<charconv>` 只实现整型 `from_chars`
  （`is_integral` 约束）与 `= delete` 的 bool 版本；浮点（float/double/
  long double）重载未实现。C++20/23 库按标准假定浮点 `from_chars` 可用即报错。
- 上游对浮点解析设计了 fast_float 回退，但通过 **CPM 在 configure 期从 GitHub 拉包**：
  禁网 CI/worker 无法完成，且会 shadow 制品仓已提供的 fast_float。

## 方案 (Solution)

1. `conanfile.py`：`requirements()` 加 `self.requires("fast_float/8.0.1")`
   （ohpcd 已发布，header-only，CMakeDeps 导出 `fast_float::fast_float`）；
   `generate()` 保留 `CMakeDeps`，OHOS 下 `CMAKE_SYSTEM_NAME=Linux`。
2. 补丁 0001：把 `CPMFindPackage(NAME FastFloat ...)` 改为

```cmake
find_package(fast_float CONFIG QUIET)
if(NOT fast_float_FOUND)
    CPMFindPackage(NAME FastFloat GIT_REPOSITORY "https://github.com/fastfloat/fast_float" GIT_TAG v8.0.2 EXCLUDE_FROM_ALL YES)
endif()
```

   并把引用目标 `FastFloat::fast_float` 改为 `fast_float::fast_float`（CMakeDeps
   实际导出的目标名）。
3. 验证：`conan create` 全绿；上游 37/37 Catch2 用例通过（unit-test 35 + lib-test 2）；
   test_ohos T3 真机浮点解析（`-d 3.14159 -f 2.5`）走 fast_float 路径断言通过；
   T4 确认 `ff_charconv` 符号编入 libmcfp.a。

## 适用边界 (Applicability / Boundary)

- **适用**：C++20/23 库在 OHOS 依赖浮点 `std::from_chars`，且上游已有
  `try_compile` 探测 + `CPMFindPackage/FetchContent` 拉 fast_float 回退。
- **边界/反例**：
  - 上游无回退、而是用编译器版本宏硬编码浮点 from_chars 能力 → 参照
    DRAFT-bitserializer（`__OHOS__` 关能力宏回退 strtod）；
  - 上游已内置编译期自动检测回退（零补丁）→ 参照 DRAFT-valijson；
  - fast_float 目标名依赖上游导出（`fast_float::fast_float` 或 CPM 时代的
    `FastFloat::fast_float`）——补丁必须按实际导出的目标名改写；
  - 仅缺整型 from_chars 或仅网络不可达而工具链有浮点 from_chars 时不适用。

## 查重差异（七轴）

| 轴 | 结果 |
|---|---|
| exact_duplicate | 否（bitserializer/valijson 用 strtod/自动检测，非预装 conan 包） |
| causal_duplicate | 否（根因同族，修复路径不同） |
| trigger_overlap | 是（同 from_chars deleted / is_integral 首错） |
| solution_overlap | 部分（fast_float 是既有方案之一，但 conan 预装 + find_package-first + 目标名改写组合未见） |
| combination_novelty | 是（fast_float conan 依赖 + CPM 优先 find_package + 目标名改写三合一） |
| boundary_novelty | 是（覆盖 C++23 charconv 浮点缺失与 CPM 网络回退双重触发） |
| test_migration_novelty | 是（test_ohos 真机浮点解析验证 fast_float 路径） |

## 关系字段

- `similar_to`: DRAFT-bitserializer-0.85.0-ohos-float-from-chars-fallback,
  DRAFT-valijson-1.1.3-ohos-float-from-chars-auto-fallback
- `caused_by`: OHOS libc++ 浮点 from_chars 缺失
- `prerequisite_of`: libmcfp 2.1.1 编译（同类 C++23 from_chars 库可复用）
- `conflicts_with`: 无

## 证据

- conan create 日志：`archives/l/libmcfp/2.1.1/reports/conan-create.log`
  （"mcfp: Using fast_float for std::from_chars"；37 用例全过；test_package 冒烟 OK）
- test_ohos：`archives/l/libmcfp/2.1.1/reports/test_ohos.log`（T3/T4 PASS）
- 双口径台账：`archives/l/libmcfp/2.1.1/test_package/MANIFEST.yml`
