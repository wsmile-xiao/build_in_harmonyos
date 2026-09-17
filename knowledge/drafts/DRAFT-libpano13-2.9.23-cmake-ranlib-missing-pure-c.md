# DRAFT-libpano13-2.9.23-cmake-ranlib-missing-pure-c

## 错误特征

纯 C/CMake 库在 OHOS 的 `conan create` 中，静态库归档阶段报：

```
[ 66%] Linking C static library libpano13.a
Error running link command: no such file or directory
make[2]: *** [CMakeFiles/pano13a.dir/build.make:725: libpano13.a] Error 2
```

共享库（`libpano13.so`）正常生成，只有静态库（`libpano13.a`）归档失败。错误出现在 cmake --build 阶段，构建目录在 conan 缓存下。

## 触发条件

- 纯 C（或 C/C++ 混编以 C 为主）库，conanfile.py 用裸 `cmake` + OHOS `ohos.toolchain.cmake` 构建
- CMakeLists.txt 在非 WIN32 分支同时产出共享库与静态库（`add_library(... SHARED)` + `add_library(...a STATIC)` 且 `OUTPUT_NAME` 相同）
- 本机探索编译（系统 PATH 含 `/data/service/hnp/bin/llvm-ranlib`）**不触发**；只有走 OHOS CMake toolchain 的 `conan create` 才暴露

## 根因

OHOS SDK 的 `native/llvm/bin/` 目录**只有 `llvm-ar`，没有 `llvm-ranlib`**。系统级软链
`/data/service/hnp/bin/llvm-ranlib → ../ohos-sdk.../llvm/bin/llvm-ar` 是唯一可用入口，但它不在
SDK 工具链目录内。

`ohos.toolchain.cmake` 将 `CMAKE_RANLIB` 硬编码为 `native/llvm/bin/llvm-ranlib`（不存在的路径）。
CMake 生成静态库后调用 ranlib 索引时执行该路径 → "no such file or directory"。

探索编译时 cmake 未走 ohos.toolchain（用的是系统 clang + 默认工具发现），PATH 下能找到
`/data/service/hnp/bin/llvm-ranlib`，所以不报错。两者工具链路径语义不同。

## 解决方案

在 conanfile.py `build()` 的 cmake 参数中显式追加：

```python
_ranlib = next((p for p in (
    "/data/service/hnp/bin/llvm-ranlib",
    os.path.join(os.path.dirname(toolchain), "../../native/llvm/bin/llvm-ranlib"),
) if os.path.exists(p)), None)
if _ranlib:
    defs.append('-DCMAKE_RANLIB="{}"'.format(_ranlib))
```

即：优先用系统软链 `/data/service/hnp/bin/llvm-ranlib`（存在），其次 SDK 相对路径探测。
一条 `-DCMAKE_RANLIB` 即可，无需 toolchain overlay 或 ranlib 包装器（那是 E385 的 Rust/cargo
子构建场景才需要的重方案）。

## 验证证据

- 修复前：`conan create . --version=2.9.23 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
  在 `[ 66%] Linking C static library libpano13.a` 处报 "Error running link command: no such file or directory"
- 修复后：`libpano13.a` 正常归档，`conan create` 全流程通过（含 test_package 的 API 调用断言）

## 与已有条目的关系（部分重复）

- **重合点（E385）**：根因相同——OHOS SDK `native/llvm/bin/` 缺 `llvm-ranlib`，`ohos.toolchain.cmake`
  把 `CMAKE_RANLIB` 固定为不存在的 SDK 内路径，静态库索引阶段失败。
- **差异点**：
  - E385 面向 **Rust crate**（`cargo build.rs`/`cmake crate` 子构建），需要生成 ranlib 包装器 +
    薄 toolchain overlay 强制覆盖 `CMAKE_RANLIB/C_COMPILER_RANLIB/ASM_COMPILER_RANLIB`，且只能
    经 target-specific `CMAKE_TOOLCHAIN_FILE` 注入；
  - 本条目面向**纯 C/CMake 库的 conan 配方**，直接在 cmake 命令行 `-DCMAKE_RANLIB=` 重指系统软链
    即可，改动最小、无包装器、无 overlay。
- **新增价值**：为纯 C/CMake 库场景提供 E385 之外的最小修复路径；`/data/service/hnp/bin/llvm-ranlib`
  软链这一可复用事实点补充进知识。E385 的 fallback（`sdk-provided-ranlib`）与本条目标的一致。

## 适用边界

- ✅ 纯 C/CMake 库 conan 配方（libpano13 2.9.23 实证）
- ✅ 同时产出 .so 与 .a 的 CMakeLists（静态归档触发 ranlib）
- ⚠️ Rust crate 子构建请优先参考 E385 的 overlay 方案（包装器注入场景）
- ❌ 不适用于修改 SDK 本体或伪造 `native/llvm/bin/llvm-ranlib`（E385 forbid 项，污染共享工具链）
