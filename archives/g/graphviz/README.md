# Graphviz

## 简介

Graphviz 是开源的图可视化软件，用于将结构化信息表示为抽象图和网络图。它包含多个布局引擎和丰富的图形输出格式。

## 功能概述

- **布局引擎**：dot（有向图）、neato（无向图）、circo（圆形布局）、fdp（力导向）、sfdp（大规模力导向）、twopi（放射布局）、patchwork（树图）
- **输出格式**：PNG、SVG、PDF、PostScript、JSON 等多种格式
- **命令行工具**：28 个可执行程序（dot、neato、circo、gvpr、acyclic 等）
- **库接口**：libgvc（核心库）、libcgraph（图结构库）、libcdt（数据结构库）

## OHOS 适配要点

### 核心问题与解决方案

**问题**：graphviz CMake 构建系统在 DT_NEEDED 条目中使用相对路径（如 `../../lib/gvc/libgvc.so`），导致运行时找不到库文件。

**解决方案**：使用静态链接构建（`BUILD_SHARED_LIBS=OFF`），完全避免动态库路径问题。

### 构建参数

```bash
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_CXX_FLAGS="-stdlib=libc++" \
  -DCMAKE_EXE_LINKER_FLAGS="-lc++ -lc++abi -static-libgcc -static-libstdc++"
```

### 已知限制

- Autotools 构建系统不适用（configure.ac 使用函数调用定义版本，autogen.sh 依赖 Git 环境）
- 动态链接版本存在相对路径问题，不适合 DESTDIR 模式打包

## 依赖关系

### 编译依赖

- cmake（构建工具）
- perl（可选，autogen.sh 需要）
- clang/clang++（编译器）

### 运行依赖

- libc++_shared.so（C++ 标准库）
- libc.so（系统 C 库）

## 产品清单

### 可执行工具（28 个）

- dot、dot_builtins、neato、circo、fdp、sfdp、twopi
- patchwork、osage、gvpr、acyclic、bcomps、ccomps
- tred、unflatten、gc、dijkstra、gml2gv、gv2gml
- gvcolor、gvgen、gvpack、mm2gv、sccmap、nop
- prune、edgepaint、cluster、gvmap

### 静态库

- libgvc.a（核心库）
- libcgraph.a（图结构）
- libcdt.a（数据结构）
- libpathplan.a（路径规划）
- libxdot.a（xdot 解析）

## 参考资料

- 官网：https://graphviz.org/
- 源码：https://gitlab.com/graphviz/graphviz
- 文档：https://graphviz.org/documentation/