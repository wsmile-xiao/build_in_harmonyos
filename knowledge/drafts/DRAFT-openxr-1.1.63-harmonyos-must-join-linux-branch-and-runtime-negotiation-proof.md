# openxr 1.1.63：`CMAKE_SYSTEM_NAME=HarmonyOS` 静默掉出 Linux 分支，以及"失败被归一化成同一码"时怎么证明 dlopen 真的发生了

## 场景一：平台族用字符串比较判定时，HarmonyOS 是一个"谁都不匹配"的新字符串

Conan 的 OHOS 工具链把 `os=OHOS` 映射成 **`CMAKE_SYSTEM_NAME=HarmonyOS`**
（`ci/conan/profiles/ohos-aarch64` 头部注释）。而上游对平台族的判定是**字符串
比较**：

```cmake
# src/CMakeLists.txt:219
if(WIN32)
    add_definitions(-DXR_OS_WINDOWS)
elseif(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    add_definitions(-DXR_OS_LINUX)
elseif(ANDROID)
    add_definitions(-DXR_OS_ANDROID)
...
```

`HarmonyOS` 既不等于 `Linux`，也不是 `ANDROID`。于是 `XR_OS_LINUX` 不定义，
下面这些**整段不参与编译**：

| 位置 | 内容 | 没有它会怎样 |
|------|------|-------------|
| `src/loader/loader_platform.hpp:28` | `#if defined(XR_OS_LINUX) \|\| defined(XR_OS_APPLE) \|\| defined(XR_OS_ANDROID)` 里的 `LoadDynamicLibrary` / `GetSymbol`（dlopen/dlclose/dlsym 封装） | **loader 的全部意义就是 dlopen 运行时**——这条没了，loader 就是空壳 |
| `src/common/platform_utils.hpp:85` | 同款 guard 里的 `PlatformUtilsGetEnv` | 读环境变量的统一入口缺失 |
| `src/loader/manifest_file.cpp:675` | `#elif defined(XR_OS_LINUX)` → `FindXDGConfigFile("openxr/", ...)`（`XDG_CONFIG_HOME` / `XDG_CONFIG_DIRS` 运行时发现） | 掉到 `:683` 的 `#else` 去调 `PlatformGetGlobalRuntimeFileName` —— 一条"系统预装运行时"的路径，OHOS 上既不存在也不对路 |

**它不是"少了点优化"，而是静默换了行为**：configure 可能过、编译可能过，
但运行期表现像另一个平台。识别信号有三个，按成本从低到高：

```sh
grep -n 'STREQUAL "Linux"' src/CMakeLists.txt        # 平台族判定是不是字符串比较
grep -rn "XR_OS_LINUX" src/ | head                   # 哪些能力被它 guard 住
# 编译期/运行期：
#   'LoadDynamicLibrary' was not declared in this scope
#   failed to determine active runtime file path for this environment
```

**修复**：把 HarmonyOS 并入 Linux 分支，只做平台并集，不引入平台宏、不依赖
HarmonyOS 特性——**可直接向上游提交**：

```cmake
-elseif(CMAKE_SYSTEM_NAME STREQUAL "Linux")
+elseif(CMAKE_SYSTEM_NAME STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
+    # HarmonyOS/OpenHarmony uses the Linux-compatible dynamic loading API
+    # (dlopen/dlclose/dlsym), and the loader's runtime discovery path is the
+    # XDG_CONFIG_HOME one guarded by XR_OS_LINUX in manifest_file.cpp.
     add_definitions(-DXR_OS_LINUX)
```

**推广**：凡上游用 `STREQUAL "<platform>"` 判定平台族，HarmonyOS 都是一次
"全部 miss"。适配前先把所有 `STREQUAL` 平台分支列出来，判断 HarmonyOS 该并
进哪一支；**不要**改 guard 本身（那会让同一份源码在其它平台编译出错误实现，
且无法上游化）。

### 反例：同一份上游源码，换构建系统后"需要的补丁集合"会变

1.1.60 的旧归档带一个给 presentation 后端加 `"none"` 的补丁。它在 Conan 工具链
下是**死代码**：

```cmake
# src/CMakeLists.txt:262
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    include(presentation)
```

`CMAKE_SYSTEM_NAME` 是 `HarmonyOS` → 这个分支不可达 → `presentation.cmake`
压根不会被 include → 不存在"BACKENDS 列表缺 none"的问题。1.1.60 需要它，是
因为那一版用自备 `toolchain.cmake` 把 `CMAKE_SYSTEM_NAME` **强制设成了
`Linux`**。同理，本配方也**不传** `PRESENTATION_BACKEND`（传了只会收获一条
unused-variable 警告）。**教训：旧归档的补丁清单不能照搬，要按当前构建系统的
实际变量重新推导。**

## 场景二：被加载方把一切失败归一化成同一错误码时，返回码不是判据

OpenXR 的 loader 通过 `dlopen` 加载运行时，二者用一个 C 入口协商：

```c
XrResult xrNegotiateLoaderRuntimeInterface(const XrNegotiateLoaderInfo* loaderInfo,
                                          XrNegotiateRuntimeRequest* runtimeRequest);
```

问题是 loader 侧最后会把**任何**失败归一化：

```cpp
// src/loader/runtime_interface.cpp:226-260  RuntimeInterface::LoadRuntime 末尾
return XR_ERROR_RUNTIME_UNAVAILABLE;   // ← "清单没找到" 与 "negotiate 失败" 同码
```

于是下面这两种完全不同的世界，从 `xrCreateInstance` 的返回值看**一模一样**：

| 世界 | 发生了什么 | `xrCreateInstance` 返回 |
|------|-----------|------------------------|
| A | 清单都没找到，压根没 dlopen | `XR_ERROR_RUNTIME_UNAVAILABLE` |
| B | 清单找到了、`.so` dlopen 成功、dlsym 到了、函数被调了、协商失败 | `XR_ERROR_RUNTIME_UNAVAILABLE` |

而 OHOS 适配的核心命题恰恰是 B 里的前半段：**loader 能不能在这个平台上把运行时
拉起来**。用返回码断言，等于什么都没证。

**对策：让被加载方自己留痕（out-of-band sentinel）。** 本适配的 stub 运行时
在协商入口里先把哨兵文件写出来，**再**返回失败：

```cpp
STUB_EXPORT XrResult XRAPI_CALL
xrNegotiateLoaderRuntimeInterface(const XrNegotiateLoaderInfo* loaderInfo,
                                  XrNegotiateRuntimeRequest* runtimeRequest) {
    const char* marker = std::getenv("OPENXR_STUB_MARKER");
    if (marker != nullptr && marker[0] != '\0') {
        std::FILE* h = std::fopen(marker, "w");
        if (h != nullptr) { std::fputs("negotiated\n", h); std::fclose(h); }
    }
    return XR_ERROR_INITIALIZATION_FAILED;   // 故意谈判失败
}
```

判据变成一句话：**哨兵文件存在 ⟺ dlopen + dlsym + 调用链全通**，与"运行时
可用不可用"彻底解耦。运行日志里还有一条 loader 侧的铁证：

```
RuntimeInterface::LoadRuntime skipping manifest file .../stub_runtime.json, negotiation failed with error -6
```

两个实现细节：`MODULE` 库必须显式 `__attribute__((visibility("default")))`
（CMake 默认 `-fvisibility=hidden` 会让符号从动态符号表消失，`dlsym` 拿到空）；
被测程序按场景 `setenv`，并在 `finally` 里恢复继承来的环境变量。

**推广**：任何"插件式加载 + 多因归一错误码"的场景（XR loader/runtime、Vulkan
layer、显卡/输入驱动加载），想验证"加载链路本身通不通"，都得换成边带证据
（文件、日志、计数器），别信返回码。

## 场景三：测试套件"静默 SKIP 仍退出 0"——ctest 退出码不区分"全跑过"与"大半跳过"

上游唯一的 ctest 目标是 `loader_test`（Catch2 v3，6 个 `TEST_CASE` /
10 个 `SECTION` / 56 个断言）。问题在于**其中 4 个用例开头就是**：

```cpp
if (!g_has_installed_runtime) { SKIP("Skipped - no runtime installed"); }
```

`g_has_installed_runtime` 取决于 loader 能否发现上游自己生成的 `test_runtime`
清单。发现不了 → 4/6 SKIP → **ctest 退出码依然是 0**，日志里只有一行
"skipped"。只看退出码就把"只跑了 2/6"当成"全绿"。

为什么清单会发现不了？因为上游生成清单时 `library_path` 用的是**裸文件名**：

```cmake
# src/tests/test_runtimes/CMakeLists.txt
gen_xr_runtime_json("${CMAKE_CURRENT_BINARY_DIR}/openxr/1/active_runtime.json"
                    "${CMAKE_CURRENT_BINARY_DIR}/$<TARGET_FILE_NAME:test_runtime>" -b)
```

`library_path` 不含 `/`，loader 会把它当**全局库名**交给 dlopen（走加载器搜索
路径）。OHOS 的 musl 加载器没有 glibc 那种兜底搜索路径，所以必须把
「构建树里所有含 `.so` 的目录 + OHOS SDK 的 `llvm/lib`（`libc++_shared.so`）」、
以及依赖包的 `lib/`，一起拼进 `LD_LIBRARY_PATH`。

**两层防御**（缺一层就会假通过）：

1. 让清单**可发现**：拼 `LD_LIBRARY_PATH`；
2. 让 SKIP**不可能被忽略**：读回 `Testing/Temporary/LastTest.log` 里的 Catch2
   汇总行，`skipped != 0`、`total < 6`、或抓不到汇总行，一律抛异常。

另外 `build()` 内的 `ctest` 失败时不会把 `LastTest.log` 打到控制台，而 CI 只
保留约 4000 字符的日志尾部——所以要在抛出前**主动**把日志尾部打到 stderr，
保证断言失败的原文落在保留区内。

**推广**：任何把"跳过"实现成正常退出路径的测试框架（Catch2 的 `SKIP`、gtest
的 `GTEST_SKIP()`、autotools 的 `SKIP` 关键字、check 的 `SKIP`），退出码都
**不能**用来判断覆盖率；必须去读汇总行。

## 场景四：`BUILD_TEST` 类开关之间的隐含耦合

关掉"测试"往往连带关掉别的，或者反过来——本适配必须**同时**打开两个开关才能
跑上游套件：

- **`BUILD_TESTS=ON`**：vendored Catch2 只在
  `if(BUILD_TESTS OR BUILD_CONFORMANCE_TESTS)`（`src/CMakeLists.txt:626`）时
  `add_subdirectory(external/catch2)`。关掉它，`loader_test` 会因为找不到
  `Catch2::Catch2` 而在 **configure** 阶段失败。
- **`BUILD_API_LAYERS=ON`**：`loader_test` 的 `add_dependencies` 指向
  `XrApiLayer_test` / `api_dump` / `core_validation`。
- 而 **`BUILD_SDK_TESTS=OFF`**：`hello_xr` 等示例需要 `XR_USE_PLATFORM_*`
  （presentation backend），HarmonyOS 下必然配置失败；`loader_test` 不受它
  管辖，关掉不丢上游测试。

**推广**：这些开关的名字都叫"测试"，但控制的是三个正交的东西（测试框架是否
存在 / 测试目标的依赖是否存在 / 示例程序是否要平台后端）。逐个 grep
`add_subdirectory` 与 `add_dependencies` 的条件，别凭名字猜。

## 场景五：消费者侧要"真消费上游的包配置"

本包安装的是上游自己的 CMake 包配置（`lib/cmake/openxr/OpenXRConfig.cmake` +
`OpenXRTargets.cmake`，NAMESPACE `OpenXR::`，目标 `OpenXR::openxr_loader` /
`OpenXR::headers`）。test_package 刻意**不用** Conan 的 CMakeDeps，而是直接把
包的 `package_folder` 交给 `CMAKE_PREFIX_PATH`，让 `find_package(OpenXR
REQUIRED)` 去消费这份上游配置——这样等于顺带验了"包对外承诺的 CMake 包配置在
安装树里真的可用"，而用 CMakeDeps 生成一份替身就把这条绕过去了。

loader 的导出符号由 version script（`src/loader/openxr-loader.map`，56 个符号）
圈定，所以 `test_package` 里额外断言
`xrGetInstanceProcAddr(XR_NULL_HANDLE, "xrCreateInstance", &fp) == XR_SUCCESS`
且 `fp != nullptr`——这是"version script 没把内核符号裁掉"的直接证据。

顺带一个易错点：`xrGetInstanceProcAddr(XR_NULL_HANDLE, <未知名>)` 返回的是
**`XR_ERROR_HANDLE_INVALID`**，不是 `XR_ERROR_FUNCTION_UNSUPPORTED`。null
instance 下 loader 只放行 `xrCreateInstance` / `xrEnumerateApiLayerProperties` /
`xrEnumerateInstanceExtensionProperties` / `xrInitializeLoaderKHR` /
`xrGetInstanceProcAddr`，其余一律在 `loader_core.cpp` 的 "it is invalid to pass
XR_NULL_HANDLE" 分支被拦下。这条给"loader 没有对任何字符串都回 SUCCESS"提供了
一个不依赖运行时的反证。
