# hermes 1.9 适配笔记

## 基本信息
- 软件: hermes 1.9 (Facebook Hermes JavaScript Engine)
- 构建系统: CMake
- 编译日期: 2026-08-06
- 编译器: clang 15.0.4 / clang++
- 状态: built (conan-verify passed, W3 timed out due to 20+ min build time)

## 源码信息
- 上游: github.com/facebook/hermes
- Tag: hermes-v260318099.0.1 (CMake VERSION 1.0.0)
- SHA256: f184e7e45b04d35680bc1687d69966fff7c47b798087eed5a8c57aedacf06a8e

## 编译步骤

```bash
mkdir build && cd build
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DHERMES_UNICODE_LITE=ON \
  -DHERMES_ENABLE_WIN10_ICU_FALLBACK=OFF \
  -DCMAKE_INSTALL_LIBDIR=lib \
  -DBOOST_CONTEXT_ARCHITECTURE=arm64 \
  -DBOOST_CONTEXT_ABI=aapcs
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ICU not found | CMake on OHOS does not skip ICU like Android | HERMES_UNICODE_LITE=ON (upstream build option, same as Emscripten/Android) |
| 2 | config.guess failed | external/llvh config.guess doesn't recognize HarmonyOS | Patch GetHostTriple.cmake: add HarmonyOS/OHOS host triple detection |
| 3 | "Unable to determine platform" | CMake on OHOS doesn't set UNIX variable | Patch Hermes.cmake: add HarmonyOS/OHOS to LLVM_ON_UNIX condition |
| 4 | Boost.Context x86_64 assembly | CMAKE_SYSTEM_PROCESSOR empty on OHOS | BOOST_CONTEXT_ARCHITECTURE=arm64 + BOOST_CONTEXT_ABI=aapcs |

## 源码修改

| 文件 | 补丁 | 说明 |
|------|------|------|
| cmake/modules/Hermes.cmake | 0001 | Add HarmonyOS/OHOS to platform detection (LLVM_ON_UNIX) |
| external/llvh/cmake/modules/GetHostTriple.cmake | 0002 | Add HarmonyOS/OHOS host triple detection |

## 验证结果

```bash
$ hermes --version
Hermes JavaScript compiler and Virtual Machine.
  Hermes release version: 1.0.0
  HBC bytecode version: 99

$ echo 'print("Hello from Hermes on HarmonyOS!");' | hermes /dev/stdin
Hello from Hermes on HarmonyOS!
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/hermes | Hermes JS engine binary |
| bin/hermesc | Hermes compiler |
| bin/shermes | Static Hermes |
| bin/hdb | Hermes debugger |
| bin/hbcdump | Hermes bytecode dump |
| bin/hvm | Hermes VM |
| bin/hcdp | Hermes CDP (Chrome DevTools Protocol) |
| include/hermes/Public/*.h | Hermes public headers |
| include/jsi/*.h | JSI (JavaScript Interface) headers |

## 注意事项

- HERMES_UNICODE_LITE=ON skips ICU dependency (same approach as Android/Emscripten builds)
- The Intl API returns errors/stubs when HERMES_UNICODE_LITE is ON
- W3 local CI simulation times out (600s) because hermes build takes ~20 minutes on OHOS
- conan-verify (G2) passed successfully, confirming the recipe works
