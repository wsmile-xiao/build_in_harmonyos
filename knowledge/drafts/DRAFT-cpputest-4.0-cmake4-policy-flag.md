# DRAFT-cpputest-4.0-cmake4-policy-flag

## 症状（可复现）
CMake>=4 配置旧项目时报：
```
CMake Error at CMakeLists.txt:8 (cmake_minimum_required):
  Compatibility with CMake < 3.5 has been removed from CMake.
```
cpputest 4.0（cmake_minimum_required(VERSION 2.8)）实测复现。

## 根因
CMake>=4 移除 <3.5 policy 兼容。关键新发现：**Conan CMakeToolchain 的 tc.variables 不适用此修复**——toolchain 文件在 project() 初始化时才加载，而 cmake_minimum_required 在其之前执行；无论 tc.variables 还是 tc.cache_variables（写入 conan_toolchain.cmake）都晚于 policy 检查。

## 已尝试方案
- ❌ `tc.variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"`：配置仍失败（toolchain 加载时机晚）。
- ✅ `cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})`：CMake helper 以 -D 命令行 cache 形态传入，配置成功（cpputest 4.0 conan create 全绿验证）。

## 最终方案
conan 配方 build()：
```python
cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
```

## 适用范围 / 反例 / 解除条件
- 适用：CMake>=4 + cmake_minimum_required<3.5。
- 反例：变量写进 toolchain 文件无效；project() 之后的 set() 无效。
- 解除条件：项目升级 cmake_minimum_required>=3.5 后可移除。

## 查重与新增价值
- E103（bump-cmake-minimum-version）：方案是改上游 CMakeLists，未涉及 conan 变量通道。
- E187（add-cmake-flag）：只给命令行结论，未区分 toolchain 变量为何无效。
- 本条补全"传参通道"维度（命令行 cache vs toolchain 文件）+ 机理（加载时机），并为 prescan 提供 CMakeLists 版本模式，属 E187 的组网补全（caused_by: E187），按组合/补全新增价值申报。

## 触发实例
- cpputest/4.0 @ HarmonyOS PC（conan 2.29.1 + CMake 4.1.2 + clang 15 OHOS），2026-09-21。
