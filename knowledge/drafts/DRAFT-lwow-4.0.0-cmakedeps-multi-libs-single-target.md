# DRAFT-lwow-4.0.0-cmakedeps-multi-libs-single-target：CMakeDeps 对多库 flat libs 包仅生成单一包 target 的消费约束

> Contributor: pc7-22 | Status: Draft | Updated: 2026-09-23
> Source: lwow 4.0.0 适配（Path B 知识库扩展，PR 与 lwow 归档同 PR）
> 对应：`knowledge/drafts/DRAFT-lwow-4.0.0-cmakedeps-multi-libs-single-target.kv`

## 问题

lwow 配方 `package_info()` 声明：

```python
self.cpp_info.libs = ["lwow_devices", "lwow"]
```

test_package 的 CMakeLists.txt 尝试链接臆想的子 target：

```cmake
target_link_libraries(test_package PRIVATE lwow::lwow lwow::lwow_devices)
```

结果两个典型错误（依 CMakeDeps 版本/路径不同）：

```
CMake Error: Target "test_package" links to: lwow::lwow_devices  but the target was not found
CMake Error: Library 'lwow_devices' not found in package
```

## 根因

Conan 2 的 CMakeDeps 对 **flat `cpp_info.libs`**（非 components）只生成
**一个包级 aggregate target**（`lwow::lwow`），**不会**为 `libs` 里的每个库
单独生成 `lwow::lwow_devices` 之类的子 target。多个库共享一个 target，
由 CMakeDeps 在链接行内部展开成 `-llwow_devices -llwow`。

要生成多 target 的唯一正规途径是 **components**：每个组件独立
`cmake_target_name`（如 `lwow::lwow_devices`）。

## 方案

### 消费端（test_package / 消费者）—— 只链接包级 aggregate target

```cmake
find_package(lwow REQUIRED CONFIG)
add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE lwow::lwow)
```

- 不按库名构造子 target。
- `libs` 顺序即链接顺序：依赖库在前（`["lwow_devices", "lwow"]`，devices 依赖 core）。

### 若下游确实需要独立子 target —— 用 components 建模

```python
def package_info(self):
    self.cpp_info.components["devices"].libs = ["lwow_devices"]
    self.cpp_info.components["devices"].requires = ["core"]
    self.cpp_info.components["devices"].set_property("cmake_target_name", "lwow::lwow_devices")
    self.cpp_info.components["core"].libs = ["lwow"]
    self.cpp_info.components["core"].set_property("cmake_target_name", "lwow::lwow")
```

## 验证

- `conan create` test_package 只链接 `lwow::lwow` → `1/1 tests passed`。
- 生成器核对：test_package/build/.../generators/lwow-Target-release.cmake 中
  只有 `lwow::lwow` 一个 target，其 INTERFACE_LINK_LIBRARIES 含两个 .a 库名。
- 消费者用例仅用 `lwow::lwow` 编译链接运行 PASSED。

## 适用边界

- **适用**：`cpp_info.libs` 声明多个库（flat）、由 CMakeDeps 消费的包及其 test_package/consumer。
- **不适用/反例**：components 建模的包（有独立子 target，可按组件链接）；header-only 包（INTERFACE，无 .a）；只声明单库的包（`lwow::lwow` 即库本身，无歧义）。

## 与既有知识的查重差异

- `similar_to`: E221（同时提供 CLI 与公开库的 Conan library 契约建模）——同涉 CMakeDeps libs/target 元数据，但 E221 主题是 application vs library 的 package_type 建模；本条目是纯库多 .a 的 CMakeDeps 单 target 生成行为与 flat libs 消费约束。
- 新增差异：明确"flat libs 多库 → 单一包 target、components 才是多 target 途径"这一边界，以及 test_package 只链 aggregate target 的修复模式。
