# binaryen 123 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-29
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published

## 编译步骤

### 1. 解压源码
```bash
cd ~/tmp
mkdir -p build-binaryen-123
tar -xzf ~/tmp/builds/binaryen-version_123.tar.gz -C ~/tmp/build-binaryen-123
cd ~/tmp/build-binaryen-123/binaryen-version_123
```

### 2. CMake 配置（关键：静态库模式）
```bash
mkdir build
cd build
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DBUILD_STATIC_LIB=ON \
  -DBUILD_TESTS=OFF \
  -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++
```

**关键参数说明**：
- `-DBUILD_STATIC_LIB=ON`：构建静态库，避免动态链接 RPATH 问题
- `-DBUILD_TESTS=OFF`：禁用测试构建，避免 googletest 依赖问题
- `-DCMAKE_INSTALL_PREFIX=$HOME/usr/local`：安装路径前缀

### 3. 编译
```bash
make -j4
```

编译耗时约 15 分钟（4 线程）。

### 4. 安装到 staging 目录
```bash
export TEST_PREFIX="$HOME/tmp/test-install-binaryen-123"
make install DESTDIR=$TEST_PREFIX
```

### 5. 验证 staging 安装
```bash
$TEST_PREFIX/$HOME/usr/local/bin/wasm-opt --version
# 输出: wasm-opt version 123
```

### 6. 生成预编译包
```bash
cd $TEST_PREFIX
tar -czf binaryen-123-ohos-aarch64.tar.gz \
  -C $TEST_PREFIX/$HOME/usr/local \
  bin lib include
```

预编译包大小：260MB（包含静态库和所有工具）

### 7. 安装到本地验证
```bash
make install
$HOME/usr/local/bin/wasm-opt --version
# 输出: wasm-opt version 123
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 动态库模式下二进制无法运行 | CMake 的 RPATH 设置为相对路径 `../../lib/libbinaryen.so`，导致安装后找不到库 | 使用静态库模式（`BUILD_STATIC_LIB=ON`），避免动态链接和 RPATH 问题 |
| 2 | CMake 配置失败：找不到 googletest 源码 | GitHub 源码包不包含 Git 子模块（googletest）内容 | 禁用测试构建（`BUILD_TESTS=OFF`） |
| 3 | 静态编译时链接错误：缺少 libc++ 符号 | 链接时未包含 C++ 标准库 | 使用系统自带的 libc++ 静态库（`libc++_static.a`），CMake 自动处理 |

## 源码修改

无需修改源码，仅通过 CMake 参数解决问题。

## 依赖版本

- cmake: 3.28+
- clang: 15.0.4（系统自带）
- libc++_static: 系统自带（/data/service/hnp/ohos-sdk.org/...）

## 验证结果

```bash
$ wasm-opt --version
wasm-opt version 123

$ wasm-as --version
wasm-as version 123

$ wasm-dis --version
wasm-dis version 123

$ readelf -d wasm-opt | grep NEEDED
  NEEDED: libc.so
```

**验证通过**：
- 所有工具可正常执行
- 静态编译无 RPATH 问题
- 只依赖 libc.so，不依赖 libbinaryen.so 或 libc++_shared.so

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| binaryen-123-ohos-aarch64.tar.gz | 260MB | 预编译包，包含所有工具和静态库 |
| libbinaryen.a | 72MB | 静态库 |
| wasm-opt | 24MB | WASM 优化工具 |
| wasm-as | 23MB | WASM 汇编工具 |
| wasm-dis | 22MB | WASM 反汇编工具 |

## 注意事项

1. **静态编译体积较大**：单个工具约 23-24MB，因为静态链接了 libbinaryen（约 72MB）。这是避免 RPATH 问题的代价。
2. **不适合作为库使用**：如果其他软件需要链接 libbinaryen，建议使用静态库 libbinaryen.a。
3. **无 RPATH 问题**：静态编译的二进制文件不需要 RPATH，可以在任何位置直接执行。
4. **googletest 缺失**：如果需要运行测试，需手动下载 googletest 源码到 `third_party/googletest/` 目录。
---

**编译结束**: 2026-05-29 11:22
**最终状态**: built
