# E429 — 上游只在 target 存在时就链接 `OpenMP::OpenMP_CXX`，构建选项置 OFF 仍会注入 `-fopenmp`

## 错误特征

```
ld.lld: error: undefined symbol: __kmpc_end_critical
>>> referenced by GenWayWayDat.cpp.obj in archive .../lib<name>_import.a
ld.lld: error: undefined symbol: __kmpc_for_static_init_8
ld.lld: error: undefined symbol: __kmpc_for_static_fini
```

消费者链接**静态库**时失败；而适配方本地 `conan create` 的构建与测试阶段全绿。

## 触发条件

- 构建系统: cmake（Conan 2 + CMakeToolchain）
- 阶段: 消费者 linking（`conan create` 的 test_package，或任何下游项目）
- 平台: OHOS / OpenHarmony（clang SDK 自带 libomp），Linux 上同样可复现

## 根因分析

上游 `CMakeLists.txt` 把 OpenMP 接线写成：

```cmake
if(TARGET OpenMP::OpenMP_CXX)
  target_link_libraries(${LIBNAME} OpenMP::OpenMP_CXX)
endif()
```

**只判断 target 是否存在，不判断自家的 `<PRJ>_BUILD_WITH_OPENMP` 选项**。两点合起来导致故障：

1. OHOS clang SDK 自带 `libomp.so` / `libomp.a` / `omp.h`，`find_package(OpenMP QUIET)` 必然成功 → target 存在；
2. 源码中的 `#pragma omp critical` / `#pragma omp parallel for` 没有 `#ifdef _OPENMP` 守卫 → 被 `-fopenmp` 编译成 `__kmpc_*` 调用。

于是静态归档留下 `__kmpc_*` 未定义符号，而 Conan 的 `package_info()` 不会声明 libomp，消费者链接必然失败。构建阶段之所以全绿，是因为构建树里该目标自己带着 `-fopenmp` 与运行时。

## 解决方案

### 推荐方案

`generate()` 中在 `CMakeToolchain` 上**同时**设置两项：

```python
tc.variables["<PRJ>_BUILD_WITH_OPENMP"] = False
tc.variables["CMAKE_DISABLE_FIND_PACKAGE_OpenMP"] = True
```

后者让 `find_package(OpenMP)` 直接返回未找到、`OpenMP::OpenMP_CXX` 目标不存在，`-fopenmp` 不再注入。无 OpenMP 时 `#pragma omp critical` 退化为普通语句块、`parallel for` 退化为串行循环，语义等价（只损失并行度）。

验证：

```bash
nm -u package/lib/lib<name>.a | grep -c __kmpc   # 期望 0
```

### 备选（确实需要多线程时）

把 `libomp` 作为 `requires` 声明，由 CMakeDeps 提供 `OpenMP::OpenMP_CXX`，消费者链接时带上运行时。代价是多一个共享库运行时依赖。

### 禁止做法

- ❌ 手工在 `CFLAGS`/`CXXFLAGS` 里加 `-fopenmp`、在 `LDFLAGS` 里加 `-lomp`，或 `#define _OPENMP`：让运行时依赖脱离 Conan 依赖图，消费者在缺 libomp 的环境下仍失败。
- ❌ 只设 `<PRJ>_BUILD_WITH_OPENMP=OFF` 就认为已关闭：这正是本次踩的坑。

## 验证

```bash
nm -u <pkg>/lib/lib<name>.a | grep -c __kmpc
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 关联条目

- 相似: E214（lld 符号裁剪，症状同为 `ld.lld: error: undefined symbol` 但根因不同）
- 原则: P001（鸿蒙是原生编译环境）、P006（不得用编译开关绕过问题）
- 实证: libosmscout 2024.06.02.1（`libosmscout-import` 的 `GenWayWayDat.cpp` 等）
