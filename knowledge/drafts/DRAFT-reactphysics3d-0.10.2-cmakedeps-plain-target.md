# DRAFT — CMakeDeps 无命名空间裸 target：test_package 链接目标必须与生成器实际产物一致

## 错误特征

`conan-verify` G2（`conan create`）在 test_package 阶段失败，CMake 配置期报
target 找不到：

```
CMake Error at CMakeLists.txt:8 (target_link_libraries):
  Target "test_reactphysics3d" links to:
    reactphysics3d::reactphysics3d
  but the target was not found.  Possible reasons include:
    * There is a typo in the target name.
    * A find_package call is missing for an IMPORTED target.
    * An ALIAS target is missing.
-- Generating done (0.0s)
CMake Generate step failed.
ERROR: reactphysics3d/0.10.2@ohpcd/stable (test package): Error in build() method, line 27
	cmake.configure()
```

把链接目标改为 `ReactPhysics3D::reactphysics3d` 同样报 target not found。

## 触发条件

- 库配方 `package_info()` 显式设置了 `cmake_file_name` 与 **不带 `::`** 的
  `cmake_target_name`：
  ```python
  self.cpp_info.set_property("cmake_file_name", "ReactPhysics3D")
  self.cpp_info.set_property("cmake_target_name", "reactphysics3d")
  ```
- test_package 用 CMakeDeps 生成器并以惯例写命名空间目标链接。
- 平台无关（本案例在 OHOS aarch64 交叉编译下触发）。

## 根因分析

Conan 2 的 CMakeDeps 生成器按 `package_info()` 属性生成：

- `cmake_file_name` → `find_package(ReactPhysics3D)` 的文件名
  （`ReactPhysics3DConfig.cmake` + `ReactPhysics3DTargets.cmake`）；
- `cmake_target_name` → IMPORTED target 名。**名中不含 `::` 时只生成裸目标**：

```cmake
if(NOT TARGET reactphysics3d)
    add_library(reactphysics3d INTERFACE IMPORTED)
    message(... "Conan: Target declared 'reactphysics3d'")
endif()
```

生成器**不会**为裸名自动补 `<cmake_file_name>::` 前缀别名，因此
`ReactPhysics3D::reactphysics3d` 与 `reactphysics3d::reactphysics3d` 都不存在。

> 对比：命名空间形态（如 `cmake_target_name="WebP::webp"`、`"Qt6::DBus"`、
> `"Taskflow::Taskflow"`）会生成对应的 `Xxx::yyy` 目标（E473/E323/E322 覆盖），
> 而裸名形态此前无条目，本次为新增差异。

## 修复方案（优先：与生成产物对齐）

1. **确认生成器实际目标名**（生成器目录在 test_package 的
   `build/<profile>/generators/`）：

   ```bash
   grep -n 'add_library' <build>/generators/ReactPhysics3DTargets.cmake
   # => add_library(reactphysics3d INTERFACE IMPORTED)  ← 裸名
   ```

2. **test_package/CMakeLists.txt 按实际产物链接**：

   ```cmake
   cmake_minimum_required(VERSION 3.15)
   project(test_reactphysics3d CXX)
   find_package(ReactPhysics3D REQUIRED)
   add_executable(test_reactphysics3d test.cpp)
   target_link_libraries(test_reactphysics3d reactphysics3d)
   enable_testing()
   add_test(NAME test_reactphysics3d COMMAND test_reactphysics3d)
   ```

3. **test() 显式运行消费者**（E298：避免 CTest 委托丢 conanrun 环境）：

   ```python
   generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
   def test(self):
       test_bin = os.path.join(self.cpp.build.bindirs[0], "test_reactphysics3d")
       self.run(f'"{test_bin}"', env="conanrun")
   ```

验证：`conan-verify reactphysics3d 0.10.2` → G0-G4 + L2/L4/L5 全 PASS，
test_package 消费者输出 `PASS: reactphysics3d 0.10.2 dynamics OK on OHOS`。

## 兜底方案（配方侧改为命名空间目标）

把 `cmake_target_name` 写成带 `::` 的形式，生成器产出命名空间目标，
test_package 链接 `ReactPhysics3D::reactphysics3d`：

```python
self.cpp_info.set_property("cmake_target_name", "ReactPhysics3D::reactphysics3d")
```

任何情况下 test_package 的链接名都必须与生成器实际产物一致，禁止臆测命名。

## 适用边界与反例

- **适用**：显式使用非命名空间 `cmake_target_name` 的 CMake 库配方；同一问题
  在 autotools→CMake 模板替换、header-only 与静态库配方中均可能出现。
- **反例**：不设置 `cmake_target_name`（默认 `name::name` 或组件形态）时
  命名空间目标存在，Test 包可链接 `name::name`，不适用本条目；带命名空间
  `cmake_target_name` 的配方不适用。

## 关联关系

- `similar_to`: E473（target not found 家族，但 E473 是依赖缺组件 target）、
  E321/E322（cmake_file_name/cmake_target_name 用法，但均为命名空间目标）
- `caused_by`: CMakeDeps 生成器对裸名 cmake_target_name 的处理
- `conflicts_with`: 无
- `prerequisite_of`: 无

来源：reactphysics3d/0.10.2 R01（pc5-14），conan-verify G2 实测
（metrics_fail_count=2，metrics_success_count=1，confidence 0.9）。