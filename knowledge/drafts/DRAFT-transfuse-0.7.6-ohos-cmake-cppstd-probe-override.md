# DRAFT-transfuse-0.7.6-ohos-cmake-cppstd-probe-override

## 一句话

OHOS profile 的 `compiler.cppstd=17` 被 `conan_toolchain.cmake` 翻译成**无条件
normal `set(CMAKE_CXX_STANDARD 17)`**，CMake 把该变量导出的 `-std=` 追加在
`CMAKE_CXX_FLAGS` 与 `CMAKE_CXX_FLAGS_RELEASE` **之后**，于是压过上游
`CHECK_CXX_COMPILER_FLAG` 自探测出来、追加进 `CMAKE_CXX_FLAGS` 的 `-std=c++20`；
命令行 `-D`、`tc.variables`、`unset()` 三条路全不通（`unset` 会退回
`CMAKE_CXX_STANDARD_DEFAULT=14`，症状换成 `std::filesystem`），**只有
`CMAKE_PROJECT_INCLUDE` 钩子里 `set` 成真实值**有效。

## 症状（两层，按尝试顺序）

1. 保持 profile 默认 17：
   `src/dom.cpp:103: error: no member named 'contains' in 'std::map<std::string_view, std::set<std::string_view>>'`
   （`std::map/std::set::contains` 是 C++20）
2. 改用 `unset(CMAKE_CXX_STANDARD)`：
   `src/filesystem.hpp:35: error: no member named 'filesystem' in namespace 'std'; did you mean 'std::__fs::filesystem'?`
   libc++ 的 `_LIBCPP_BEGIN_NAMESPACE_FILESYSTEM` 只有在 C++17 以上才是 inline 命名空间

## 根因（flag 顺序，实测）

`flags.make` 的 `CXX_FLAGS` 实测（unset 版本）：

```
-stdlib=libc++ -Wall ... -fPIC -Wconversion -flto -fvisibility-inlines-hidden \
-std=c++20 -O3 -DNDEBUG -fPIE -std=c++14
                         ↑ 上游探测        ↑ 配置级   ↑ 最后一个生效 ⇒ 14
```

`CMAKE_CXX_STANDARD` 为空时 CMake 用 `CMAKE_CXX_STANDARD_DEFAULT`，clang 15 的默认
是 gnu++14，于是 `-std=c++14` 依旧排在最后 —— **unset 与设错值落点完全一样**。

## 四条路逐条实测

| 尝试 | 结果 | 原因 |
|---|---|---|
| `-DCMAKE_CXX_STANDARD=20` | ✗ | toolchain 用 normal `set()`，屏蔽 cache 与命令行 |
| `tc.variables["cppstd"] = 20` | ✗ | Conan 2.29 `CppStdBlock.context()` 只读 `settings.compiler.cppstd`，无变量/conf 开关 |
| 钩子里 `unset(CMAKE_CXX_STANDARD)` | ✗ | 回退 `CMAKE_CXX_STANDARD_DEFAULT=14`，仍追加在最后 |
| 钩子里 `set(CMAKE_CXX_STANDARD 20)` | ✓ | 末尾只剩 `-std=c++20` |

## 方案

`generate()` 落盘钩子，`tc.cache_variables["CMAKE_PROJECT_INCLUDE"]` 指向它
（该 cache variable 经 `CMakePresets.json` 的 `cacheVariables` 抵达 CMake，
**不写进 conan_toolchain.cmake**，排查时别去 toolchain 里找）：

```cmake
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
```

配套的 `-L` / ICU data 补法见配对条目
`DRAFT-transfuse-0.7.6-pkgconfig-findmod-split-l-and-icu-data`。

## 边界

- 上游若**自己** `set(CMAKE_CXX_STANDARD ...)`（而不是探测追加 flags），toolchain
  的 normal 变量在 toolchain 之后被覆盖，本来就没问题；本条只命中「探测追加
  CMAKE_CXX_FLAGS」这一形态；
- 钩子运行在 `project()` 之后的 top-level 目录作用域，所以能压过 toolchain 的
  normal `set()`，且被 `add_subdirectory()` 继承；
- `variable_watch(CMAKE_CXX_STANDARD conan_modify_std_watch)` 只会打一条
  "has been modified by ..." 警告，不阻断。

## 证据

- transfuse 0.7.6，`profile ohos-aarch64-wsl`（`compiler.cppstd=17`），clang 15.0.7
- 修正后 `link.txt` 尾段：`-std=c++20 -O3 -DNDEBUG -flto`，无 `c++17`/`c++14` 残留
- 配方：`archives/t/transfuse/0.7.6/`；修正后 14 个上游 ctest 用例全过

## 判重说明

- `archives/a/arg_router/1.3.0` 用 `unset` 解决同类覆盖，但那是「上游用
  `if(NOT DEFINED CMAKE_CXX_STANDARD)` 决定标准」的形态，`unset` 正好让它回到默认；
  本条上游无条件探测并追加 flags，`unset` 反而招来 `-std=c++14`，方向相反 ⇒ 不判重；
- E176 = ICU 动态库加载面；E355 = `.pc` prefix 面 ⇒ 均不同层。