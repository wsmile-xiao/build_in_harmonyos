# DRAFT-tidy-5.8.0-cmake4-minimum-version-compat-removed：cmake 4.x 移除 <3.5 兼容，老工程 `cmake_minimum_required` configure 即死

> Contributor: sunjunyang | Status: Draft | Updated: 2026-09-22
> Source: tidy 5.8.0 适配（本配方 PR），`CMakeLists.txt:20 VERSION 2.8.12`
> 对应：`knowledge/drafts/DRAFT-tidy-5.8.0-cmake4-minimum-version-compat-removed.kv`

## 现象

平台工具链为 cmake 4.4.3（harmonybrew 提供；制品仓 `conan list "cmake/*" -r=ohpcd`
为 0，无 cmake 包）。凡 `cmake_minimum_required(VERSION < 3.5)` 的工程，
configure 第一步即失败：

```console
CMake Error at CMakeLists.txt:20 (cmake_minimum_required):
  Compatibility with CMake < 3.5 has been removed from CMake.

  Update the VERSION argument <min> value.  Or, use the <min>...<max> syntax
  ...
  Or, add -DCMAKE_POLICY_VERSION_MINIMUM=3.5 to try configuring anyway.
```

2014-2020 年代项目（声明 2.8.x/3.0 的）普遍命中。

## 根因与两个关键约束

CMake 4.0 移除了对 `< 3.5` 的兼容。修复路径受两个平台事实约束：

1. **该检查发生在 `project()` 之前**，而 conan 的 `conan_toolchain.cmake`
   是在 `project()` 初始化时才被读入——所以经
   `tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"` 注入
   （落在 toolchain 文件里）**实测无效**，configure 依旧报同一错误；
2. 本仓惯例不 `tool_requires("cmake/...")`（制品仓无 cmake 包；老版本
   3.16.3 也已从上游源清库）——"换 cmake 3"的绕法在平台不成立。

## 方案（一行 build-fix 补丁）

```diff
-cmake_minimum_required (VERSION 2.8.12)
+cmake_minimum_required (VERSION 3.5)
```

以 `patch_type: build-fix` 进配方的 conandata patches。语义零变化：
3.5 早已是事实基线。tidy 打上后库 + console + 消费者测试全链路通过。

## 禁止动作

1. **试图装旧版 cmake**（tool_requires cmake/3.x 或本地装 cmake 3）：
   制品仓没有 cmake 包，环境 4.4.3 是唯一工具，绕一圈回到原点。
2. **用 CMakeToolchain variables 注入 CMAKE_POLICY_VERSION_MINIMUM**：
   实测无效（检查先于 toolchain 读入），只会制造"已处理"假象。

## 验证

```sh
grep -n "cmake_minimum_required" CMakeLists.txt   # 期望 VERSION >= 3.5
cmake -B build && cmake --build build             # 期望 configure 通过
```
