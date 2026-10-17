# conan toolchain 预设 C++17 压制 ECM 的 C++20 自动判定

> DRAFT-solid-6.26.0-conan-toolchain-cppstd17-blocks-ecm-cpp20（知识库扩展草稿，路径 B）
> 与 solid 6.26.0 归档同 PR 交付。

## 问题

在 HarmonyOS PC（`os=OHOS`, `compiler=clang 15`, profile `compiler.cppstd=17`）上对
KDE Frameworks solid 6.26.0 执行真实构建，CMake configure 成功，首次编译即失败：

```text
/storage/.../solid-6.26.0/src/solid/devices/frontend/device.cpp:226:19:
error: no member named 'contains' in 'std::map<Solid::DeviceInterface::Type,
       std::unique_ptr<Solid::DeviceInterface>>'
    if (!m_ifaces.contains(type)) {
        ~~~~~~~~ ^
```

`std::map::contains` 是 C++20（P0458R2）新增成员，C++17 下不存在。

## 根因

1. ECM 自身是会按编译器能力自动选标准的：`ECM/kde-modules/KDECompilerSettings.cmake:403-408`

   ```cmake
   if (NOT CMAKE_CXX_STANDARD)
       if (<compiler is recent enough>)
           set(CMAKE_CXX_STANDARD 20)
       else()
           set(CMAKE_CXX_STANDARD 17)
       endif()
   endif()
   ```

2. 但 conan 生成的 `conan_toolchain.cmake` 在 `project()` **之前**就已设置了该变量：

   ```cmake
   message(STATUS "Conan toolchain: C++ Standard 17 with extensions OFF")
   set(CMAKE_CXX_STANDARD 17)
   set(CMAKE_CXX_STANDARD_REQUIRED ON)
   variable_watch(CMAKE_CXX_STANDARD conan_modify_std_watch)
   ```

   于是 `if (NOT CMAKE_CXX_STANDARD)` 永假，ECM 的自动判定失效，整个工程被钉在 C++17。

3. 两个"看起来能用"的写法都无效（实测）：
   - `cmake -B build -DCMAKE_CXX_STANDARD=20`：toolchain 里的 `set()` 覆盖 cache 值，
     configure 输出仍是 `Conan toolchain: C++ Standard 17`；
   - 只用 `tc.variables["CMAKE_CXX_STANDARD"] = "20"`：仍在 toolchain 内被同一
     段代码压制（kcoreaddons 6.26.0 因此改用 `CMAKE_CXX_FLAGS=-std=c++20` 兜底）。

## 修复（推荐）

在 `conanfile.py` 的 `configure()` 中覆盖 cppstd —— conan 随即把 toolchain 生成成
`set(CMAKE_CXX_STANDARD 20)`，同时保留 conan 自己的 `-stdlib=libc++` 等标志：

```python
def configure(self):
    # solid 6.26.0 源码使用 C++20（std::map::contains）
    # conan_toolchain.cmake 在 project() 之前设定 CMAKE_CXX_STANDARD=17，
    # 使 ECM KDECompilerSettings 的 `if (NOT CMAKE_CXX_STANDARD)` 自动判定失效
    self.settings.compiler.cppstd = "20"
```

修复后实测（solid 6.26.0）：

```text
$ grep -n "C++ Standard" build/Release/generators/conan_toolchain.cmake
56:message(STATUS "Conan toolchain: C++ Standard 20 with extensions OFF")
57:set(CMAKE_CXX_STANDARD 20)
```

构建继续推进到下一个真实问题（`libmount.h` 缺失，见 solid 6.26.0 notes.md），
最终 `conan create` exit 0、上游 ctest 4/4 通过。

## 回退方案

`tc.variables["CMAKE_CXX_STANDARD"]="20"` + `CMAKE_CXX_STANDARD_REQUIRED=ON` +
`tc.variables["CMAKE_CXX_FLAGS"]="-std=c++20"`（kcoreaddons/6.26.0 口径）。注意
`CMAKE_CXX_FLAGS` 是整体覆盖，可能挤掉 conan 注入的编译标志，仅在 cppstd 覆盖不可行时使用。

## 禁止做法

- 只传 `-DCMAKE_CXX_STANDARD=20` 或只在配方里写 `tc.variables`：假修复，仍是 C++17；
- 把上游 C++20 代码改写成 C++17 兼容代码：无必要修改上游，脱离 KDE 主线。

## 适用范围

使用 conan 构建、且实际需要高于 profile `compiler.cppstd` 的 CMake 项目，尤其是
KDE Frameworks 6.2x（solid 6.26.0 `std::map::contains`、kcoreaddons 6.26.0
`std::ranges`）。与 E293（C++17 移除旧语言特性）方向相反，`similar_to: E293`。
