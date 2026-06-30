# E081: cmake 项目缺少或不完整的 config-cmake.h.in

## 现象

cmake 项目在 configure 或 make 阶段报错：

1. `CMake Error: File xxx/config-cmake.h.in does not exist` — cmake CONFIGURE_FILE 找不到模板文件
2. `error: use of undeclared identifier 'PACKAGE_STRING'` — config.h 中缺少宏定义

## 根因

部分 cmake 项目（特别是同时支持 cmake 和 autotools 的双构建系统项目）的 `config-cmake.h.in` 文件：

- **缺失**: 源码提取过程中丢失或构建系统不包含该文件
- **语法错误**: 使用了 autotools `@...@` 变量语法而非 cmake `${...}` 语法
- **不完整**: 只定义了 `PACKAGE_STRING` 和 `SIZEOF_LONG`，缺少 `PACKAGE` 和 `VERSION` 等宏

## 解决方案

### 推荐方案: 创建/修复 config-cmake.h.in

创建完整的 cmake 模板文件，使用 `${...}` 变量语法：

```c
#ifndef CONFIG_H
#define CONFIG_H

#cmakedefine WORDS_BIGENDIAN

#define SIZEOF_LONG ${SIZEOF_LONG}

/* Package name and version */
#define PACKAGE "${PACKAGE}"
#define VERSION "${VERSION}"
#define PACKAGE_STRING "${PACKAGE_STRING}"

#endif /* CONFIG_H */
```

确保 CMakeLists.txt 中已定义 `PACKAGE`、`VERSION`、`PACKAGE_STRING` 变量：

```cmake
SET(PACKAGE ${PROJECT_NAME})
SET(VERSION ${PROJECT_VERSION})
SET(PACKAGE_STRING "${PACKAGE} ${VERSION}")
```

### 回退方案: target_compile_definitions

如果无法创建模板文件，可在 CMakeLists.txt 中直接添加编译定义：

```cmake
target_compile_definitions(target PRIVATE
    PACKAGE_STRING="libdiscid 0.6.5"
    PACKAGE="libdiscid"
    VERSION="0.6.5"
)
```

## 禁止

- ❌ 不要在 cmake 项目中使用 `@...@` 变量语法（虽然 cmake 支持，但与 autotools 混用易造成混淆）
- ❌ 不要只定义 `PACKAGE_STRING` 而忽略 `PACKAGE` 和 `VERSION`（某些源码需要所有三个宏）

## 关联

- E007: config.guess/config.sub 平台检测（类似平台适配问题）
- E072: autotools 项目构建修复
- R6: 源码修改必须追踪
- R8: 源码"四不"准则
- R23: 平台检测机制优先于改生成文件

## 示例案例

**libdiscid 0.6.5-r0**: 原始 tarball 包含 `config-cmake.h.in` 但使用 `@PACKAGE_STRING@` 和 `@SIZEOF_LONG@` 语法，且缺少 `PACKAGE` 和 `VERSION` 定义。修复后使用 `${...}` 语法并补充所有必要宏定义。