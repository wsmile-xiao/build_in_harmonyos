# Conan 2 CMake.build() 不支持 jobs 关键字：用 CMAKE_BUILD_PARALLEL_LEVEL 控制并行度

- **草稿 ID**: DRAFT-lsd2-1.9.9-conan-cmake-build-jobs-kwarg
- **来源**: lsd2 1.9.9（tothuhien/lsd2）HarmonyOS PC 适配
- **分类**: cmake / conan / build-system
- **状态**: 本地草稿（随 lsd2 1.9.9 归档同 PR 提交，路径 B 知识库扩展）

## 问题 / 错误签名

- `conan create` 时：`TypeError: CMake.build() got an unexpected keyword argument 'jobs'`
- 复现：conanfile.py `build()` 写 `cmake.build(jobs=1)`（对旧版/错误 API 的依赖），
  Conan 2.29 的 `CMake.build()` 不接受 jobs 参数。

## 根因

Conan 2 的 `conan.tools.cmake.CMake.build()` 移除了 jobs 关键字；
并行度应通过 CMake 变量 `CMAKE_BUILD_PARALLEL_LEVEL`（toolchain 注入）或生成器参数控制。
若同时需要 R9 单线程（鸿蒙 SELinux/FS 拒绝 make jobserver mkfifo，见 E074），
在 `CMakeToolchain.generate()` 中设置该变量为 1 即可同时满足两者。

## 最小修复方案（在 archives/l/lsd2/1.9.9 范围内）

1. `generate()`：`tc.variables["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"`（R9 单线程）。
2. `build()`：移除 jobs 参数，仅 `cmake.build()`。

## 验证结果

- `ohc-run.py conan-verify lsd2 1.9.9`：G2 conan create 通过（此前 TypeError 失败），
  G1-G4 + L2/L4/L5 全 PASS。

## 适用边界

- **适用**：Conan 2 conanfile.py build() 中写 `cmake.build(jobs=N)` 的配方；
  R9 单线程 + FS jobserver 限制场景（OHOS）。
- **不适用**：无需限制并行度的普通配方（不加变量即可，但 jobs 关键字仍是错误的）。
- **与 E074 关系**：E074 覆盖"make -j jobserver FIFO 拒绝 → 命令行 -j1"；
  本草稿覆盖"Conan 2 CMake.build() API 无 jobs 参数 → toolchain 变量"，
  二者是同一语义（单线程）的不同实现层（命令行 vs Conan API）。

## 反例 / 相互冲突

- 若继续使用 `cmake.build(jobs=N)` 而期望并行：Conan 2 直接 TypeError，G2 失败。

## 关系

- similar_to: E074
- caused_by: (无)
- prerequisite_of: (无)
- conflicts_with: (无)