# E748 — CMake 4.x 原生构建找不到 conan Boost 组件：CMP0167/FindBoost 模块路径与 BoostConfig 不兼容

> Draft: E748-draft-7c6b97d9 — pairs with the same-stem `.kv`

## 错误特征

绕开 conan toolchain 的**原生** cmake configure（`-DCMAKE_PREFIX_PATH` 指向
CMakeDeps 生成器目录）时：

```
-- Performing Test HAS_FUNCTION_TDESTROY - Success
Policy CMP0167 is not set: The FindBoost module is removed.  Run "cmake_policy..."
CMake Error at …/cmake-4.1/Modules/FindPackageHandleStandardArgs.cmake:227 (message):
  Could NOT find Boost: missing: unit_test_framework
  (found /…/generators/BoostConfig.cmake
   /…/cmake-4.1/Modules/FindBoost.cmake:641 (find_package_handle_standard_args))
```

自相矛盾的三行同屏：**明明找到了 BoostConfig.cmake，却说组件 missing**，
且错误栈来自 `FindBoost.cmake`——这就是「config 被当 hint、组件定位仍走
模块变量表」的混合形态。

## 根因分析

- CMake 3.30+ 用策略 **CMP0167** 移除 FindBoost 模块，`find_package(Boost)`
  改为读 `BoostConfig.cmake`；
- 上游 CMakeLists 若 `cmake_minimum_required(VERSION 3.10)`（老于 3.30）且
  没设该策略，CMake 4.x 按旧策略继续走 FindBoost 模块路径；
- 模块按自己的变量表（`Boost_UNIT_TEST_FRAMEWORK_LIBRARY` 等）定位库文件，
  与 CMakeDeps 生成的 BoostConfig 变量体系不兼容 → `missing:
  unit_test_framework`；
- **conan create 不受影响**：`conan_toolchain.cmake` 自带
  `set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)`（实测第 137 行），
  find_package 直接走 config 模式，组件目标 `Boost::unit_test_framework`
  正常声明。

## 解决方案

原生（非 conan）构建/验证轮加一个开关即可，零侵入：

```bash
cmake -S <src> -B <build> ... -DCMAKE_FIND_PACKAGE_PREFER_CONFIG=ON
```

**验证**（naive-tsearch 0.1.1，2026-09-25 设备）：同命令修前 rc=1（上贴），
修后 configure rc=0、`ctest` 3/3 Passed。

## 备选

`cmake_policy(SET CMP0167 NEW)` 或把 `find_package(Boost …)` 显式改 `CONFIG`
——都要动上游 CMakeLists；原生验证轮是本工作区自有动作，优先命令行开关。
