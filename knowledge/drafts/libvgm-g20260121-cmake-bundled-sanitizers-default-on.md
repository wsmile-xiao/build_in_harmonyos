# libvgm g20260121 — 上游 CMake 内置 sanitizers 模块且默认开启（draft）

**Category**: build-system | ohos · **Severity**: 2 · **Tool**: cmake/conan

## 症状

若沿用上游默认选项构建，configure 后所有目标被追加 `-fsanitize=address,undefined`
类编译/链接参数；在 OHOS 真机（clang 15.0.4，无 sanitizer 运行时库）上表现为链接
失败（找不到 `libclang_rt.asan*` 等）或产物一运行即 abort。

libvgm 的具体形态（g20260121，master `57585ea`）：

```cmake
option(USE_SANITIZERS "use sanitizers" ON)          # 根 CMakeLists.txt，默认 ON
list(APPEND CMAKE_MODULE_PATH ".../cmake/sanitizers")
find_package(Sanitizers)                            # 自带的 FindSanitizers.cmake
if(USE_SANITIZERS)
    add_sanitizers(vgm-utils)                       # 每个子目标逐一注入
    add_sanitizers(vgm-audio) ...
endif()
```

## 根因

1. 上游为自身 CI/调试 convenience 在仓库内置 `cmake/sanitizers/` 模块
   （FindASan/FindMSan/FindTSan/FindUBSan），默认 `USE_SANITIZERS=ON`。
2. 该选项在桌面 Linux CI 环境无害（gcc/clang 自带 runtime），但在目标设备
   工具链上没有对应 runtime，注入即坏。
3. conan 配方若只关 `BUILD_TESTING` 等常见开关、漏查项目自带模块，就会中招。

## 对策

CMakeToolchain 显式关闭：

```python
tc.variables["USE_SANITIZERS"] = False
```

识别方法：`grep -rn "sanitizers\|USE_SANITIZERS\|add_sanitizers" CMakeLists.txt cmake/`，
凡是 `option(... ON)` + `find_package(Sanitizers)` 组合的都属此族。

## 验证

libvgm g20260121 配方关闭后真机（HarmonyOS aarch64，clang 15.0.4）
`conan create` + test_package 全绿（17 断言），编译参数无任何 -fsanitize。
