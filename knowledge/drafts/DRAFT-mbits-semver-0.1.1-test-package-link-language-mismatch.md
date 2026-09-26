# DRAFT-mbits-semver-0.1.1-test-package-link-language-mismatch：test_package 源文件扩展名与工程语言声明不一致导致 Cannot determine link language

> Contributor: pc4-36 | Status: Draft | Updated: 2026-09-22
> Source: mbits-semver 0.1.1 适配（task mbits-semver-0.1.1-r01-pc4-36）
> 对应：`knowledge/drafts/DRAFT-mbits-semver-0.1.1-test-package-link-language-mismatch.kv`

## 现象

conan create 在 test_package 配置阶段即失败：

```text
CMake Error: Cannot determine link language for target "test_mbits-semver".
CMake Error: CMake can not determine linker language for target: test_mbits-semver
```

## 根因

CMake 依据源文件**扩展名**推断语言（`.c`=C、`.cpp/.cc`=C++）。
test_package 的 `CMakeLists.txt` 声明 `project(test_mbits-semver CXX)`（CXX-only，
未启用 C 语言），但 `add_executable` 的源文件扩展名是 `.c`（内容实际是 C++）
→ CMake 无法为该目标确定链接语言，早于任何编译即失败。

## 修复

内容为 C++ 时把源文件重命名为 `.cpp`，同步更新 CMakeLists/MANIFEST 引用：

```cmake
add_executable(test_mbits-semver test.cpp)
```

（或必须保留 `.c` 扩展名时，在 `project(...)` 中显式声明 C 语言。）

## 验证

重命名后 `conan create` G2 PASS，test_package ctest 2/2 Passed。

## 适用边界 / 反例

- ✅ 工程声明 CXX-only 且源文件扩展名为 `.c`
- ❌ 工程已启用 C/C++ 双语言 → 不触发此错误
- ❌ 修复后把 test_package 写成只打印字符串的空壳 → 违反 R34

## 查重关系

- similar_to: E353（同属 CMake 链接/目标判定域，机制不同：E353=目标名不匹配）
