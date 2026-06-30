# fbthrift 2020.08.24.00 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-13
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `ohc-run.py init-build fbthrift 2020.08.24.00 --url=https://github.com/facebook/fbthrift/archive/refs/tags/v2020.08.24.00.tar.gz`
2. `cd $BUILD_SRC_DIR && mkdir build && cd build`
3. `cmake -DCMAKE_SYSTEM_NAME=OHOS -DBUILD_TESTS=OFF -Dcompiler_only=ON -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX ..`
4. `make -j2 thrift1 && make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | FindBoost 模块缺失 | cmake 4.1.2 移除了 FindBoost 模块 | 手动设置 Boost_INCLUDE_DIRS 和 Boost_LIBRARIES |
| 2 | thrift compiler 生成目录 CMakeLists.txt 需修改 | 缺少 Boost include 路径 | 添加 Boost_INCLUDE_DIRS 到 include_directories |

## 源码修改

- `CMakeLists.txt`: 手动添加 `set(Boost_INCLUDE_DIRS ...)` 和 `set(Boost_LIBRARIES ...)`，将 Boost 路径加入 include_directories
- `thrift/compiler/generate/CMakeLists.txt`: 同样添加 Boost include 路径

## 依赖版本

- openssl: 1.1.1w
- boost: 1.87.0
- flex: 2.6.4
- bison: 3.8.2
- gflags: 2.2.2
- glog: 0.7.1

## 验证结果

```bash
thrift1 --version
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| fbthrift-2020.08.24.00-ohos-aarch64.tar.gz | ~5MB | Release包（仅 thrift compiler） |
| fbthrift-2020.08.24.00-ohos-aarch64-debug.tar.gz | ~8MB | Debug包 |

## 注意事项

- 仅编译 thrift compiler (compiler_only=ON)，完整 fbthrift 库需要更多依赖（folly, wangle 等）
- cmake 4.1.2 无 FindBoost 模块，需手动指定 Boost 路径
---
**编译结束**: 2026-06-13 21:04
**最终状态**: built
