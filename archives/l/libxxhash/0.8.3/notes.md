# libxxhash 0.8.3 编译笔记

## 编译信息
- 版本: 0.8.3
- 构建系统: CMake (cmake_unofficial/)
- 编译日期: 2026-07-15
- 编译器: Clang 15.0.4 (aarch64-linux-ohos)

## 编译过程

### Step 1: 准备源码
- 源码下载自 GitHub: https://github.com/Cyan4973/xxHash/archive/refs/tags/v0.8.3.tar.gz
- SHA256: aae608dfe8213dfd05d909a57718ef82f30722c392344583d3f39050c7f29a80
- 解压到工作目录

### Step 2: 编译

#### 构建命令
```bash
cd $BUILD_SRC_DIR
mkdir -p cmake_unofficial/build
cd cmake_unofficial/build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release
make -j2
make install DESTDIR=$TEST_PREFIX
```

#### 遇到的问题
无。xxHash 0.8.3 的 CMake 构建系统直接支持 HarmonyOS 平台，无需补丁。

### Step 3: 测试
```bash
make check
# 所有测试通过（49948 个 sanity 测试）
```

### Step 4: 安装
```bash
make install
# 安装产物: libxxhash.a, xxhash.h, xxh3.h
```

### Step 5: 用户验证
```bash
xxhsum --version
# xxhsum 0.8.3 by Yann Collet
# compiled as 64-bit aarch64 + NEON little endian with Clang 15.0.4

echo "Hello, HarmonyOS!" | xxhsum
# b276811e74c526d7  stdin
```

## 知识提取

### 平台兼容性
- xxHash 0.8.3 源码天然支持 HarmonyOS/OpenHarmony 平台
- CMake 构建系统自动检测 aarch64 + NEON 架构
- 无需任何补丁

### 与 0.8.2 的差异
- 0.8.2 使用 Makefile 构建时需要补丁（添加 HarmonyOS 到 install 目标过滤列表）
- 0.8.3 使用 CMake 构建，无需补丁

## 依赖关系
- 构建依赖: 无
- 运行时依赖: 无
---

**编译结束**: 2026-07-15 23:39
**最终状态**: built
