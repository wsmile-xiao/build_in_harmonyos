# llvm-project 20.1.8（HarmonyOS PC · LLVM + Clang 开发面单包交付）

## 定位

一个包同时提供 **LLVM 20.1.8 与 Clang 20.1.8 的开发面**（dev face），供下游在 CMake 里
`find_package(LLVM)` / `find_package(Clang)` 并链接 clang 组件库使用。典型消费者：
**ispc 1.28.2**（其 `cmake/FindLLVM.cmake` + `CMakeLists.txt` 同时需要 `llvm-config`、
`LLVMConfig.cmake` 与 `libclangFrontend.a` 等 6 个 clang 组件静态库）。

为什么必须单包（依赖项任务根因）：

| 库中现状 | 缺口 |
|---|---|
| `llvm/20.1.0`（ohpcd, OHOS armv8） | 只有 LLVM（`lib/cmake/llvm` + `include/llvm` + 组件静态库），**无 Clang** ⇒ ispc configure 得 `clangFrontendPath-NOTFOUND` |
| `clang/20.1.8`（ohpcd） | 远端包**损坏**（`conan download` 报 `doesn't contain a conan_package.t file`），不可用 |
| `clang/22.1.8`（ohpcd） | 完整 Clang dev，但是 **LLVM 22**，超出 ispc 1.28.2 目标区间 |

## 包内交付面

```
lib/cmake/llvm/LLVMConfig.cmake             # LLVM 组件依赖图 + LLVMExports
lib/cmake/llvm/LLVMConfigVersion.cmake
lib/cmake/clang/ClangConfig.cmake           # 内部 find_package(LLVM <ver> EXACT) + ClangTargets
lib/cmake/clang/ClangTargets.cmake
lib/cmake/clang/ClangTargets-release.cmake
libLLVM.so / libLLVM.so.20.1 / libLLVM-20.so
libLLVM*.a                                  # 全部 LLVM 组件静态库（llvm-config --libfiles 直接给全路径）
libclangFrontend.a libclangBasic.a libclangEdit.a libclangLex.a
libclangSupport.a libclangASTMatchers.a     # + 其余全部 clang 组件静态库
libclang-cpp.so libclang.so                 # 兜底聚合动态库
include/llvm/** include/llvm-c/** include/clang/** include/clang-c/**
bin/llvm-config bin/FileCheck bin/llvm-lit bin/llvm-as bin/clang bin/clang++ bin/llc bin/opt ...
```

后端：`LLVM_TARGETS_TO_BUILD="AArch64;ARM;X86"`（**不是** AArch64-only——见下）。

## 关键适配点

1. **后端必须含 AArch64 + ARM + X86**（与 `llvm/20.1.0`、`clang/20.1.8`、`clang/22.1.8` 的
   AArch64-only 不同）。ispc 1.28.2 的 `cmake/FindLLVM.cmake` 用
   `llvm-config --targets-built` 判定 `LLVM_SUPPORTS_ARM = (含 AArch64 且含 ARM)`；
   不满足则 `ARM_ENABLED=OFF`，而 aarch64 宿主上 `X86_HOST` 也是 OFF
   ⇒ `CMakeLists.txt:357` `FATAL_ERROR "Either X86, ARM, WASM or XE targets need to be enabled."`。
   另外 ispc 在 `X86_ENABLED=ON` 时用 `clang++ --target=x86_64-unknown-unknown -march=core2 -emit-llvm`
   生成 dispatch bitcode、并为 x86 目标生成 builtins（其 lit 套件有 167 个 `REQUIRES: X86_ENABLED` 用例）。
2. **真机原生编译**（aarch64→aarch64）：不设 `CMAKE_SYSTEM_NAME` ⇒ `CMAKE_CROSSCOMPILING=FALSE`
   ⇒ `llvm-tblgen`/`clang-tblgen` 原生编+跑，绕开交叉编译的 tblgen 主机版难题。
3. **`cmake/config.guess` stub**：设备 `uname -s = HarmonyOS`，LLVM 的 `config.guess` 不认，
   而 `config-ix.cmake` 无条件调 `get_host_triple`（`-DLLVM_HOST_TRIPLE` 挡不住）⇒ build() 内覆盖为
   `#!/bin/sh\necho aarch64-unknown-linux-ohos`。
4. **`Platform/HarmonyOS.cmake` 垫片**：cmake 无 HarmonyOS 平台模块 ⇒ `UNIX` 未置 ⇒
   `HandleLLVMOptions` "Unable to determine platform" FATAL；提供 `include(Platform/Linux)` 垫片挂到
   `CMAKE_MODULE_PATH`（仍不设 `CMAKE_SYSTEM_NAME`）。
5. **动态聚合库瘦身**：`LLVM_BUILD_LLVM_DYLIB=ON` + `LLVM_LINK_LLVM_DYLIB=ON`，避免 bin/ 工具静态内嵌
   导致单文件超制品仓上限；组件静态库仍全部安装（下游 `llvm-config --libfiles` 需要）。
6. **自包含**：关掉 ZLIB/ZSTD/LIBXML2/TERMINFO/LIBEDIT/LIBPFM；runtimes 不源码构建，运行资源
   （clang_rt crt/builtins、libunwind.a、libc++abi.a）在 `package()` 内从设备 SDK 复制
   （**不**复制 SDK 的 `libc++.so`/`libc++_shared.so`，R26 合规）。
7. **ELF 代码签名**：OHOS XPM 要求 dlopen 的 `.so` 与被 exec 的可执行文件都签名，
   `package()` 内用 `binary-sign-tool -selfSign 1` 统一重签。

## 下游消费契约（CMake）

`package_info()` 用 `cmake_find_mode="none"` + `builddirs=["lib/cmake/llvm","lib/cmake/clang"]`，
CMakeToolchain 会把这两个目录放进 `CMAKE_PREFIX_PATH`，因此：

```cmake
find_package(LLVM REQUIRED CONFIG)    # 命中 <pkg>/lib/cmake/llvm/LLVMConfig.cmake
find_package(Clang REQUIRED CONFIG)   # 命中 <pkg>/lib/cmake/clang/ClangConfig.cmake
find_library(clangFrontendPath NAMES libclangFrontend.a clang-cpp HINTS ${LLVM_LIBRARY_DIRS})
```

**注意**：`package_type = "library"` ⇒ `bindirs` 不进 PATH。需要 `llvm-config` 的消费者（如 ispc 的
`find_program(llvm-config)`）必须显式传路径：

```python
dep = self.dependencies["llvm-project"]
tc.variables["LLVM_CONFIG_EXECUTABLE"] = os.path.join(dep.package_folder, "bin", "llvm-config")
# 或把 dep.cpp_info.bindirs[0] 前置进 PATH
```

## 构建与验证

```sh
conan create archives/l/llvm-project/20.1.8 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="llvm-project/*"
```

详见 `notes.md`（适配过程、测试口径与验证读数）与 `test_package/MANIFEST.yml`（上游测试声明）。
