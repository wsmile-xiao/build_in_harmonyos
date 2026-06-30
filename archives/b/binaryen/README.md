# binaryen

binaryen是一个WebAssembly编译器工具链和优化器。

## 描述

binaryen是一个用C++编写的编译器工具链和优化器库，旨在帮助编译器生成高效、优化且紧凑的WebAssembly代码。它包含多个实用工具：

- **wasm-opt**: WebAssembly优化器，可优化WASM模块的大小和性能
- **wasm-as**: WebAssembly汇编器，将文本格式转换为二进制格式
- **wasm-dis**: WebAssembly反汇编器，将二进制格式转换为文本格式
- **wasm2js**: 将WebAssembly转换为JavaScript
- **wasm-merge**: 合并多个WebAssembly模块
- **wasm-metadce**: 删除未使用的元数据
- **wasm-shell**: WebAssembly shell（测试工具）

## 鸿蒙适配说明

在鸿蒙系统上编译binaryen需要解决以下问题：

1. **CMake RPATH问题（重要）**
   - CMake动态库模式在鸿蒙平台上的RPATH处理错误
   - 相对路径`../../lib/libbinaryen.so`导致安装后找不到库
   - **必须使用静态库模式（`BUILD_STATIC_LIB=ON`）**

2. **googletest依赖缺失**
   - GitHub源码包不包含Git子模块（googletest）内容
   - 需禁用测试构建（`BUILD_TESTS=OFF`）

3. **静态编译体积较大**
   - 单个工具约23-24MB（静态链接了72MB的libbinaryen）
   - 这是避免RPATH问题的代价

## 构建参数（关键）

```bash
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DBUILD_STATIC_LIB=ON \
  -DBUILD_TESTS=OFF \
  -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++
```

**关键参数**：
- `-DBUILD_STATIC_LIB=ON`：静态库模式，避免RPATH问题
- `-DBUILD_TESTS=OFF`：禁用测试，避免googletest依赖

## 依赖

- cmake >= 3.4
- clang / clang++

## 版本列表

| 版本 | 状态 | 发布日期 | 补丁数 | 备注 |
|------|------|---------|--------|------|
| 123 | built | 2026-05-29 | 0 | 静态编译，260MB预编译包 |

## 参考

- 官方网站: https://github.com/WebAssembly/binaryen
- 文档: https://github.com/WebAssembly/binaryen/wiki
- 知识条目: CMake RPATH问题（静态库解决方案）