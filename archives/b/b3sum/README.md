# b3sum — OpenHarmony 编译档案

## 软件简介

b3sum 是基于 BLAKE3 哈希算法的命令行工具，用于计算文件的 BLAKE3 哈希值。BLAKE3 是一种快速、安全的加密哈希算法，具有以下特点：

- **高性能**: 比 SHA-256、SHA-512 等传统算法快得多
- **安全性**: 基于 BLAKE2 的安全设计，经过充分的安全分析
- **并行化**: 支持多线程和 SIMD 指令加速
- **可扩展**: 支持可扩展输出长度

本归档基于 BLAKE3 C 库实现构建简化版 b3sum 命令行工具，支持 OpenHarmony aarch64 平台。

## 可用版本

| 版本 | 状态 | 构建系统 | 说明 |
|------|------|----------|------|
| 1.8.4 | ✅ success | cmake | 简化版实现，基于 BLAKE3 C 库 |

## 构建命令

```bash
# 标准构建流程
ohc-run.py init-build b3sum 1.8.4
cd b3sum-1.8.4.work

# CMake 配置（启用 NEON SIMD 加速）
cmake -B build \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DBLAKE3_SIMD_TYPE=neon-intrinsics \
  -DCMAKE_BUILD_TYPE=Release

# 编译
cmake --build build

# 安装
cmake --install build --prefix $DEFAULT_PREFIX
```

## 补丁清单

### 1.8.4 版本

| 补丁文件 | 作用 |
|----------|------|
| `0001-CMakeLists.txt.patch` | 添加 b3sum 可执行文件构建目标 |
| `0002-b3sum.c.patch` | 新增 b3sum 命令行工具源码 |

## 已知限制

1. **简化版实现**: 本版本基于 BLAKE3 C 库创建简化版 b3sum，非完整 Rust 实现
2. **功能限制**: 不支持以下高级功能：
   - Keyed hash（密钥哈希）
   - Derive key（密钥派生）
   - 递归目录哈希
   - 输出格式选项（仅支持 hex）
3. **平台限制**: 仅支持 aarch64 架构，依赖 NEON SIMD 指令集

## 功能验证

```bash
# 基本用法
echo "hello" | b3sum
# 输出: ea9b8c4b...

# 文件哈希
b3sum /path/to/file

# 指定输出长度
b3sum -l 64 /path/to/file  # 64 字节输出

# 静默模式
b3sum -q /path/to/file
```

## 编译注意事项

1. **源码来源**: 使用 BLAKE3 GitHub release tarball 中的 `c/` 子目录
2. **SIMD 配置**: aarch64 平台推荐使用 `neon-intrinsics` 获得最佳性能
3. **构建依赖**: 需要 CMake 3.16+ 和 C99 编译器
4. **测试套件**: BLAKE3 C 库无内置测试套件，需手动验证功能
