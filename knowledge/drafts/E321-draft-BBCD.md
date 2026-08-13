# E321 — Qt 模块需 qtshadertools 的 Qt6ShaderTools_DIR

## 错误特征

```
CMake Error at src/multimedia/CMakeLists.txt:XX (qt_internal_add_shaders):
  Unknown CMake command "qt_internal_add_shaders".
```

## 触发条件

- 构建系统: cmake
- 阶段: configuration
- 适用: 使用 `qt_internal_add_shaders` 预编译 shader 的 Qt 6 子模块
  （qtmultimedia、qtquick3d、qt3d 等）

## 根因分析

Qt 6 子模块的 `qt_internal_add_shaders` CMake 宏由 **qtshadertools** 包提供，
必须通过 `Qt6ShaderTools_DIR` 让 CMake 找到该宏，否则 configure 阶段直接
报 `Unknown CMake command`。qtshadertools 包内 `lib/cmake/Qt6ShaderTools`
即为该宏的定义位置。

## 解决方案

### 推荐方案

`CMakeToolchain`（conan 配方 generate()）显式设置：

```
-DQt6ShaderTools_DIR=<qtshadertools 包>/lib/cmake/Qt6ShaderTools
```

同时将 qtshadertools 加入 requirements，并把其 package_folder 写入
CMAKE_PREFIX_PATH，保证 `Qt6ShaderToolsConfig.cmake` 可被发现。

### 禁止做法

- ❌ 仅把 qtshadertools 加进 requirements 而不设置 `Qt6ShaderTools_DIR`
  （find_package 不搜索子包内嵌的宏目录，configure 仍失败）
- ❌ 手工拷贝 `qt_internal_add_shaders` 宏到本包（破坏依赖原子性）

## 验证

```bash
grep -rE "Unknown CMake command.*qt_internal_add_shaders" build/log
# 空输出即已修复
```
