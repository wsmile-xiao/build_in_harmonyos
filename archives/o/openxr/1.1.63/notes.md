# openxr 1.1.63 — HarmonyOS PC 适配笔记

## 1. 概览

| 项 | 值 |
|----|----|
| 上游 | https://www.khronos.org/openxr/ （KhronosGroup/OpenXR-SDK-Source） |
| 版本 | 1.1.63（tag `release-1.1.63`） |
| 源码 | `https://github.com/KhronosGroup/OpenXR-SDK-Source/archive/refs/tags/release-1.1.63.tar.gz` |
| SHA256 | `a3b97a36f11abe256a7ea1668a0a468aac9b738e94bea6b468f0ae31ad537a46` |
| 构建 | CMake（Conan `CMakeToolchain`） |
| 包类型 | shared-library（`libopenxr_loader.so` + `include/openxr/*.h` + `lib/cmake/openxr/` + `lib/pkgconfig/openxr.pc`） |
| 依赖 | 无（零 Conan 依赖；运行期只要 libc / libdl / libc++_shared） |
| 补丁 | `0002-src-CMakeLists.txt.patch`（1 个） |

产出的是 **loader**（`libopenxr_loader.so`），不是运行时：应用链 loader，
loader 在 `xrCreateInstance` 时通过 `dlopen` 去加载真正的 XR 运行时。这也决定了
本包的验证重点 —— 不是"XR 功能可用"，而是"loader 在 OHOS 上能不能按 OpenXR
的 loader/runtime 协商协议把运行时拉起来"。

## 2. 补丁 0002：HarmonyOS 必须并进 Linux 分支

Conan 的 OHOS 工具链把 `os=OHOS` 映射成 `CMAKE_SYSTEM_NAME=HarmonyOS`
（`ci/conan/profiles/ohos-aarch64` 头部注释），而上游是用**字符串比较**来判定
平台族的：

```cmake
# src/CMakeLists.txt:219
elseif(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    add_definitions(-DXR_OS_LINUX)
```

`HarmonyOS` 匹配不到 `Linux`，于是 `XR_OS_LINUX` 不定义。后果不是"少了点
优化"，而是两条关键路径整段消失：

1. `src/loader/loader_platform.hpp:28` 的 `#if defined(XR_OS_LINUX) ||
   defined(XR_OS_APPLE) || defined(XR_OS_ANDROID)` —— dlopen / dlclose / dlsym
   的封装（`LoadDynamicLibrary` / `GetSymbol` / 路径规范化）在这里面。
2. `src/common/platform_utils.hpp:85` 的同款 guard —— `PlatformUtilsGetEnv`
   在这里面，Linux/OHOS 下它走 `getenv`，其它平台走另一套。

即使这两处侥幸编过，运行时发现也会走错分支：`src/loader/manifest_file.cpp:654`
先用 `XR_RUNTIME_JSON`，找不到才落到 `:675` 的 `#elif defined(XR_OS_LINUX)` →
`FindXDGConfigFile("openxr/", ...)`（XDG_CONFIG_HOME / XDG_CONFIG_DIRS）。
`XR_OS_LINUX` 没定义就会掉到 `:683` 的 `#else` 分支，去调
`PlatformGetGlobalRuntimeFileName` —— 那是个"系统预装运行时"的路径，在 OHOS 上
既不存在也不对路。

补丁把 `HarmonyOS` 并入 Linux 分支：

```cmake
-elseif(CMAKE_SYSTEM_NAME STREQUAL "Linux")
+elseif(CMAKE_SYSTEM_NAME STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
+    # HarmonyOS/OpenHarmony uses the Linux-compatible dynamic loading API
+    # (dlopen/dlclose/dlsym), and the loader's runtime discovery path is the
+    # XDG_CONFIG_HOME one guarded by XR_OS_LINUX in manifest_file.cpp.
     add_definitions(-DXR_OS_LINUX)
```

### 2.1 为什么 1.1.60 的 0003（presentation）没有移植

1.1.60 归档带 `0003-src-cmake-presentation.cmake.patch`，给 presentation 的
`BACKENDS` 列表加了一个 `"none"`。在 Conan 体系下这是**死代码**：

```cmake
# src/CMakeLists.txt:262
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    include(presentation)
```

`CMAKE_SYSTEM_NAME` 是 `HarmonyOS`，这个分支不可达 → `presentation.cmake` 压根
不会被 include → 也就不存在"BACKENDS 列表里缺 none"的问题。1.1.60 需要它，
是因为那一版用自备 `toolchain.cmake` 把 `CMAKE_SYSTEM_NAME` 强制设成了 `Linux`。

同理，本配方**不传** `PRESENTATION_BACKEND`：传了只会收获一条
unused-variable 警告。

## 3. 构建选项决策

| 选项 | 值 | 理由 |
|------|----|------|
| `DYNAMIC_LOADER` | ON | 应用侧要的是能 dlopen 运行时的共享 loader；静态裸库在 XR 场景下没有意义 |
| `BUILD_LOADER` | ON | 本包的主体 |
| `BUILD_TESTS` | **ON** | vendored Catch2 只在 `if(BUILD_TESTS OR BUILD_CONFORMANCE_TESTS)`（`src/CMakeLists.txt:626`）时才 `add_subdirectory`；关掉它 `loader_test` 会因找不到 `Catch2::Catch2` 而 configure 失败 |
| `BUILD_API_LAYERS` | ON | `loader_test` 的 `add_dependencies` 指向 `XrApiLayer_test` / `api_dump` / `core_validation`（`src/CMakeLists.txt:640` 只在 `BUILD_TESTS` 下进 `tests/`，但 api layer 目标来自这里） |
| `BUILD_SDK_TESTS` | **OFF** | `hello_xr` / `list` / `list_json` / `c_compile_test` 需要 `XR_USE_PLATFORM_*`，也就是需要 presentation backend；HarmonyOS 下必然配置失败。`loader_test` 不受它管辖，关掉不丢上游测试 |
| `BUILD_CONFORMANCE_TESTS` | OFF | 需要 `xr_use_graphics_api_*` + 真实运行时，还会拉起 `BUILD_CONFORMANCE_CLI`（依赖 python 脚本链） |
| `BUILD_WITH_SYSTEM_JSONCPP` | OFF | 用随包 vendored jsoncpp（制品仓没有 jsoncpp 包） |
| `BUILD_ALL_EXTENSIONS` | OFF | 与 1.1.60 一致 |

## 4. 上游测试：loader_test 是本包的回归判据

### 4.1 全树只有一个 ctest 目标

`grep -rn "add_test\|enable_testing"` 在非 vendored 代码里只命中一次：

```cmake
# src/tests/loader_test/CMakeLists.txt:72
add_test(NAME loader_test COMMAND loader_test
         WORKING_DIRECTORY "$<TARGET_FILE_DIR:loader_test>")
```

它是 Catch2 v3 写的，**6 个 TEST_CASE / 10 个 SECTION**：
`TestEnumLayers`、`TestEnumInstanceExtensionProperties`、`TestCreateDestroyInstance`、
`TestGetSystem`、`TestCreateDestroyAction`、`TestLoaderInitialize`。

### 4.2 最大的坑：4/6 会被静默 SKIP，ctest 照样退出 0

`loader_test.cpp` 里 6 个 TEST_CASE 有 4 个开头就是：

```cpp
if (!g_has_installed_runtime) { SKIP("Skipped - no runtime installed"); }
```

`g_has_installed_runtime` 取决于 loader 能否发现上游自己生成的 test_runtime
清单。发现不了 → 4 个用例 SKIP → **ctest 退出码依然是 0**，日志里只有一行
"skipped"。只看退出码就会把"大半没跑"当成"全绿"。

因此 `conanfile.py` 的 `_assert_testsuite_bounds()` 直接读
`Testing/Temporary/LastTest.log`，解析 Catch2 的汇总行：

- 抓不到汇总行 → 失败（"the upstream suite did not run"）；
- `skipped != 0` → 失败；
- `total < MIN_UPSTREAM_TESTS(=6)` → 失败。

### 4.3 要跑起来还得先让 loader 找到 test_runtime

上游生成清单时用的是**裸文件名**：

```cmake
# src/tests/test_runtimes/CMakeLists.txt
gen_xr_runtime_json("${CMAKE_CURRENT_BINARY_DIR}/openxr/1/active_runtime.json"
                    "${CMAKE_CURRENT_BINARY_DIR}/$<TARGET_FILE_NAME:test_runtime>" -b)
```

`library_path` 不含 `/`，`manifest_file.cpp` 的 `CreateIfValid` 就会把它当
**全局库名**交给 dlopen —— 也就是走加载器的搜索路径。OHOS 加载器没有像 glibc
那样的兜底搜索路径，所以 `_runtime_libdirs()` 把三样东西拼进 `LD_LIBRARY_PATH`：

1. 依赖包的 `lib/`（本包无 Conan 依赖，通常为空）；
2. **构建树里所有含 `.so` 的目录**（`os.walk`，含 `libtest_runtime.so`、
   `libXrApiLayer_test.so`、api_dump、core_validation）；
3. OHOS SDK 的 `native/llvm/lib`（`libc++_shared.so` 在那，dlopen 出来的 .so 的
   `DT_NEEDED` 里有它）。

另外 `loader_test` 在 `XR_OS_LINUX` 下自己把 `XDG_CONFIG_HOME` 指向
`current_path().parent_path() / "test_runtimes"`，这也要求补丁 0002 生效 ——
否则 loader 不会走 XDG 分支，清单照样发现不了、用例照样 SKIP。**补丁 → 分支 →
清单可发现 → 用例真跑** 是一条链。

### 4.4 CI 日志只能看见尾部

CI 侧只保留约 4000 字符的日志尾部，ctest 默认失败时并不把
`LastTest.log` 打到控制台。所以配方在 ctest 抛 `ConanException` 时主动调
`_dump_ctest_logs()` 把 `LastTest.log` 的最后 3000 字符打到
`self.output.error`，保证断言失败的原文落在保留区内。

## 5. test_package：怎么证明"loader 真的 dlopen 了运行时"

### 5.1 问题的核心：返回码分不出来

`RuntimeInterface::LoadRuntime`（`src/loader/runtime_interface.cpp:226-260`）在
末尾把**任何**失败统一归一化成 `XR_ERROR_RUNTIME_UNAVAILABLE`：

```
// RuntimeInterface::LoadRuntime 末尾
return XR_ERROR_RUNTIME_UNAVAILABLE;
```

于是 "清单都没找到" 和 "找到了运行时、dlopen 成功、negotiate 失败" 返回**完全
同一个码**。想断言"OHOS 上 loader 能 dlopen 运行时"，看
`xrCreateInstance` 的返回值是徒劳的。

### 5.2 解法：让 stub 运行时自己留痕

`test_package/stub_runtime.cxx` 是一个最小运行时，只导出 loader 唯一会找的入口：

```cpp
STUB_EXPORT XrResult XRAPI_CALL
xrNegotiateLoaderRuntimeInterface(const XrNegotiateLoaderInfo* loaderInfo,
                                  XrNegotiateRuntimeRequest* runtimeRequest);
```

它**故意让谈判失败**（返回 `XR_ERROR_INITIALIZATION_FAILED`），但在返回前先把
环境变量 `OPENXR_STUB_MARKER` 指向的文件写出来。判据因此变成：

> 哨兵文件存在 ⟺ loader 真的 dlopen 了 stub、dlsym 到了
> `xrNegotiateLoaderRuntimeInterface`、并且真的调进来了。

这与"运行时可用不可用"完全解耦，是 OHOS dlopen/dlsym 链路唯一可靠的证据。

`visibility("default")` 是必需的：`add_library(... MODULE)` 配合 CMake 默认的
`-fvisibility=hidden` 会让符号消失，dlsym 到手就是空。

### 5.3 三个场景

| # | 场景 | 断言 | 证明什么 |
|---|------|------|---------|
| A | `XR_RUNTIME_JSON` 不设，`XDG_CONFIG_HOME`/`XDG_CONFIG_DIRS` 指向空目录 | `xrCreateInstance == XR_ERROR_RUNTIME_UNAVAILABLE`，且哨兵**不存在** | 无运行时时的确定性行为；且这条只有在 `manifest_file.cpp` 的 `XR_OS_LINUX` 分支被编出来时才成立 → 补丁 0002 生效 |
| B | `xrGetInstanceProcAddr(XR_NULL_HANDLE, "xrCreateInstance", &fp)` | `== XR_SUCCESS` 且 `fp != nullptr` | loader 的 version script（`openxr-loader.map`，56 个符号）没把内核符号裁掉 |
| B' | `xrGetInstanceProcAddr(XR_NULL_HANDLE, "xrNotARealFunction", &fp)` | `== XR_ERROR_HANDLE_INVALID` 且 `fp == nullptr` | 反证"不是任何字符串都回 SUCCESS"。注意期望码是 `XR_ERROR_HANDLE_INVALID` 而非 `XR_ERROR_FUNCTION_UNSUPPORTED`：null instance 下 loader 只放行 4 个函数（`xrGetInstanceProcAddr` / `xrInitializeLoaderKHR` / `xrEnumerateApiLayerProperties` / `xrEnumerateInstanceExtensionProperties` / `xrCreateInstance`），其余一律在 `loader_core.cpp` 的 "it is invalid to pass XR_NULL_HANDLE" 分支被拦下 |
| C | `XR_RUNTIME_JSON` 指向合法清单 + `OPENXR_STUB_MARKER` | 哨兵文件**出现** | **鸿蒙特有**：loader 能在 OHOS 上 dlopen 一个运行时并调进协商入口（本适配的核心价值） |

### 5.4 刻意不吃 Conan 的 CMakeDeps

消费者（`test_package/CMakeLists.txt`）用上游**自己安装**的包配置：

```cmake
find_package(OpenXR REQUIRED)                 # → lib/cmake/openxr/OpenXRConfig.cmake
target_link_libraries(test_openxr PRIVATE OpenXR::openxr_loader)
add_library(stub_runtime MODULE stub_runtime.cxx)
target_link_libraries(stub_runtime PRIVATE OpenXR::headers)
```

`test_package/conanfile.py` 不给 `CMakeDeps`，只把
`openxr.package_folder` 塞进 `CMAKE_PREFIX_PATH`。这样等于同时验了
`OpenXRConfig.cmake` / `OpenXRTargets.cmake`（NAMESPACE `OpenXR::`）在安装树里
真的可用 —— 这是包对外承诺的一部分，用 CMakeDeps 生成一份替身就绕过去了。

## 6. 与 1.1.60 归档的差异

| 项 | 1.1.60（legacy，无 conanfile.py） | 本包 1.1.63 |
|----|-----------------------------------|-------------|
| 构建入口 | 自备 `toolchain.cmake`，`CMAKE_SYSTEM_NAME` 强设 Linux | Conan `CMakeToolchain`，`CMAKE_SYSTEM_NAME=HarmonyOS` |
| 补丁 | 0002 + 0003（presentation 加 `none`） | 只有 0002（0003 死代码，见 §2.1） |
| 测试 | `BUILD_TESTS=OFF`，不跑上游套件 | `BUILD_TESTS=ON`，配 `BUILD_API_LAYERS=ON` 实跑 `loader_test`，并校验不 SKIP |
| 验证 | 符号表 + 手工加载脚本，无 dlopen 链路证据 | test_package 用哨兵运行时证明 dlopen+dlsym+调用全通 |
| 包配置 | 未验 | `find_package(OpenXR)` + `pkg-config openxr` 由 test_package 实消费 |

## 7. 验证记录

CI（OHOS aarch64 原生 worker）中 `conan create` 顺序执行：

1. 打补丁 → configure（`CMAKE_SYSTEM_NAME=HarmonyOS`，带 `-DXR_OS_LINUX`）→
   build loader + vendored jsoncpp + 3 个 api layer + Catch2 + loader_test；
2. `ctest` 实跑 `loader_test`，`_assert_testsuite_bounds()` 断言
   **6 个 TEST_CASE 全部执行、0 个 SKIP**；
3. 安装 → test_package configure（`find_package(OpenXR)`）→ 编出
   `test_openxr` 与 `libstub_runtime.so` → 运行 6 条断言（§5.3 的 A/B/B'/C）。
