# blake3 1.8.3 — OpenHarmony 编译记录

## 基本信息
- 软件: blake3
- 版本: 1.8.3
- 构建系统: CMake
- 目标: ohos-aarch64
- 源码 URL: https://github.com/BLAKE3-team/BLAKE3/archive/refs/tags/1.8.3.tar.gz

## 软件简介
BLAKE3 是一种快速的加密哈希函数，比 BLAKE2、SHA-1、SHA-2 和 SHA-3 更快。
本软件为 C 实现，提供静态库和头文件。

## 编译指导

### 环境要求
- cmake >= 3.9
- clang/gcc 编译器
- aarch64 架构（自动启用 NEON SIMD 优化）

### 编译命令
```bash
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=$HOME/usr/local -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)
cmake --install build
```

### 特殊处理
- 源码结构特殊：CMakeLists.txt 位于 c/ 子目录，init-build 会自动提升
- 无可执行文件：仅生成静态库 libblake3.a
- NEON SIMD：aarch64 平台自动启用

## 补丁清单
无补丁。

## 已知限制
1. 仅提供静态库，无动态库
2. 无独立可执行文件（需通过 example.c 自行编译）
3. 无官方测试套件（需手动功能验证）

## 功能验证
```bash
# 使用静态库编译示例程序
cc -O3 -o example example.c -I$HOME/usr/local/include -L$HOME/usr/local/lib -lblake3

# 测试哈希功能
echo "Hello, BLAKE3!" | ./example
# 输出: 97d98f9f3dfb049733684ea8273febd8ff77a1f45cd765abc7e9b613debf4867
```

## 安装产物
- lib/libblake3.a - 静态库
- include/blake3.h - 头文件
- lib/cmake/blake3/*.cmake - CMake 配置文件
- lib/pkgconfig/libblake3.pc - pkg-config 配置
