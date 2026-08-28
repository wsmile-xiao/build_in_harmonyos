# OHOS clang 拒绝 `-stdlib=libstdc++`（Conan profile libcxx 误配导致编译器检查 broken）

> **结构化数据**: [graph/DRAFT-ecm629-stdlib-libstdcxx-invalid.kv](../graph/DRAFT-ecm629-stdlib-libstdcxx-invalid.kv)
> **严重度**: 🟡 medium | **阶段**: configuration | **工具**: conan / cmake / clang
> **来源**: extra-cmake-modules 6.29.0 首轮本地适配（conan create 首次失败）

---

## 错误特征

```
clang-15: error: invalid library name in argument '-stdlib=libstdc++'
-- Check for working CXX compiler: /data/service/hnp/bin/clang++ - broken
CMake Error ... The C++ compiler "/data/service/hnp/bin/clang++" is not able
to compile a simple test program.
```

或 configure 阶段报告编译器 TryCompile 失败、`Check for working CXX compiler ... broken`。

## 根因

Conan profile 中 `compiler.libcxx=libstdc++11`（或任意 `libstdc++` 变体）时，
`CMakeToolchain` 生成的 `conan_toolchain.cmake` 会注入 `-stdlib=libstdc++`；
OHOS 工具链 clang 15 只提供 **libc++**，直接拒绝该 flag：

```
clang-15: error: invalid library name in argument '-stdlib=libstdc++'
```

这使 CMake 的 TryCompile 失败 → `Check for working CXX compiler ... broken` → configure 中断。

## 影响范围

所有以 Conan 2（`CMakeToolchain`）构建到 **OHOS aarch64** 的 C++ 配方，
若使用 `libcxx=libstdc++11` 的默认/误配 profile（`conan profile detect` 常生成该值）。

## 解决方案

### 方案 1（推荐）：使用仓库预置 OHOS profile

改用 `ci/conan/profiles/ohos-aarch64`（其 `compiler.libcxx=libc++`），
`CMakeToolchain` 注入 `-stdlib=libc++`，编译器检查与 test_package 正常运行：

```bash
conan create . --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64
```

### 方案 2（回退）：修正 profile 的 libcxx

```bash
conan profile update settings.compiler.libcxx=libc++ default
```

## 验证

```bash
conan profile show | grep -i libcxx   # 应输出 libc++
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → exit 0, test_package ./test_ecm 退出码 0
```

## ⛔ 禁止

- 不要在 recipe 里写死 `-stdlib=libstdc++` 或改 toolchain 文件——OHOS clang 仍拒绝，
  且违反 R33（编译器 flag 不可在 recipe 内裸写，需由 Conan Toolchain 提供）。

## 与现有条目差异

- **E191**（`unable to find library -lc++` / `-lc++abi`）：是 **链接阶段**找不到 libc++/libc++abi
  共享库，方案为 `-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` 绕过链接测试；
  本条目是 **configuration 阶段** clang 直接拒绝 `-stdlib=libstdc++` flag，E191 的绕过方案
  无法解决此错误，二者 error_signature / 根因 / 修复均不同。
- **E130**（`nullptr_t` / `__abi_tag__`）：是 OHOS libc++ 头文件要求 C++17+，与本条目无关。
- **E092 / E140**（CMake 平台识别 / `CMAKE_SYSTEM_NAME=HarmonyOS`）：CMake 对 HarmonyOS
  "System is unknown" 的 warning 在本库为非阻塞 fallback，未触发平台检测失败，故复用不适用。

---

*DRAFT-ecm629-stdlib-libstdcxx-invalid · 2026-08-27 · extra-cmake-modules 6.29.0 首轮适配*
