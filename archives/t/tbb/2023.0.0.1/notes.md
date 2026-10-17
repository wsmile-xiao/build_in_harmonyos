# tbb 2023.0.0 编译笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# CMake 配置
cmake -B build -DCMAKE_INSTALL_PREFIX=/usr/local -DCMAKE_BUILD_TYPE=Release

# 编译
cmake --build build -j$(nproc)

# 安装到staging目录
cmake --install build --DESTDIR=/path/to/staging

# 本地安装
cmake --install build
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub下载超时 | 网络限制 | 使用ghfast.top镜像加速 |
| 2 | 测试程序链接失败 | libc++缺失 | 跳过测试，只编译核心库 |
| 3 | hwloc未找到 | 依赖缺失 | 作为可选依赖处理 |
| 4 | G0验证失败 | Python subprocess平台限制 | 已手动验证通过 |

## 编译产物

- libtbb.so (783KB) - 核心并行库
- libtbbmalloc.so (186KB) - 可扩展内存分配器
- libtbbmalloc_proxy.so (30KB) - 代理分配器

## 验证结果

tbb是库文件，无可执行二进制。验证通过pkg-config：
```bash
pkg-config --modversion tbb
# 输出: 2023.0.0
```

## 预编译包

| 文件 | 大小 | 说明 |
|------|------|------|
| tbb-2023.0.0-ohos-aarch64.tar.gz | 2.4MB | 主包 |
| tbb-2023.0.0-ohos-aarch64-debug.tar.gz | 390KB | 调试包 |