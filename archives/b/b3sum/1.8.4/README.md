# b3sum 1.8.4 — OpenHarmony 编译记录

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件 | b3sum |
| 版本 | 1.8.4 |
| 构建系统 | cmake |
| 目标平台 | ohos-aarch64 |
| 编译状态 | ✅ success |
| 编译日期 | 2026-04-24 |

## 编译指导

### 源码获取

本版本使用 BLAKE3 C 库实现（完整仓库的 `c/` 子目录）构建：

```bash
# 源码 URL
https://api.github.com/repos/BLAKE3-team/BLAKE3/tarball/1.8.4
```

### 构建命令

```bash
# 初始化构建环境
ohc-run.py init-build b3sum 1.8.4
cd /storage/Users/currentUser/tmp/builds/b3sum-1.8.4.work

# CMake 配置
cmake -B build \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DBLAKE3_SIMD_TYPE=neon-intrinsics \
  -DCMAKE_BUILD_TYPE=Release

# 编译
cmake --build build -j$(nproc)

# 安装到 staging 目录
cmake --install build
```

### CMake 配置选项说明

| 选项 | 值 | 说明 |
|------|-----|------|
| `CMAKE_INSTALL_PREFIX` | `/storage/Users/currentUser/usr/local` | 安装路径 |
| `BLAKE3_SIMD_TYPE` | `neon-intrinsics` | ARM64 NEON SIMD 加速 |
| `CMAKE_BUILD_TYPE` | `Release` | 发布版本优化 |

## 补丁清单

### 0001-CMakeLists.txt.patch

**作用**: 添加 b3sum 可执行文件构建目标

**修改内容**:
- 新增 `b3sum` 可执行文件目标
- 链接 `blake3` 静态库
- 设置安装规则

### 0002-b3sum.c.patch

**作用**: 新增 b3sum 命令行工具源码

**修改内容**:
- 实现简化版 b3sum 命令行工具
- 支持 stdin/file 哈希计算
- 支持输出长度设置（-l 参数）
- 支持静默模式（-q 参数）

## 已知限制

### 功能限制

1. **简化版实现**: 本版本基于 BLAKE3 C 库创建，非完整 Rust b3sum 实现
2. **缺失功能**:
   - ❌ Keyed hash（密钥哈希）
   - ❌ Derive key（密钥派生）
   - ❌ 递归目录哈希
   - ❌ 多种输出格式（仅支持 hex）

### 平台限制

1. **架构**: 仅支持 aarch64 架构
2. **SIMD**: 依赖 NEON intrinsics，旧款 ARM 处理器可能不兼容

## 功能验证

### 基本验证命令

```bash
# stdin 哈希计算
echo "hello world" | b3sum
# 预期输出: 长度 64 字符的十六进制哈希值

# 文件哈希计算
echo "test content" > /tmp/test.txt
b3sum /tmp/test.txt

# 指定输出长度
b3sum -l 32 /tmp/test.txt  # 32 字节输出

# 静默模式（仅输出哈希值）
b3sum -q /tmp/test.txt
```

### 验证结果

| 测试项 | 结果 | 说明 |
|--------|------|------|
| stdin 输入 | ✅ 通过 | 正常计算管道输入哈希 |
| 文件输入 | ✅ 通过 | 正常计算文件哈希 |
| 输出长度 | ✅ 通过 | -l 参数正确设置输出长度 |
| 静默模式 | ✅ 通过 | -q 参数正常工作 |
| NEON 加速 | ✅ 通过 | SIMD 指令正常执行 |

## 预编译包

| 文件 | 说明 |
|------|------|
| `b3sum-1.8.4-ohos-aarch64.tar.gz` | 发布版预编译包 |
| `b3sum-1.8.4-ohos-aarch64-debug.tar.gz` | 调试符号包 |
| `install-b3sum-1.8.4.sh` | 安装脚本 |

## 编译注意事项

1. **源码结构**: GitHub tarball 包含完整仓库，实际使用 `c/` 子目录
2. **SIMD 配置**: aarch64 平台必须使用 `neon-intrinsics` 获得最佳性能
3. **无测试套件**: BLAKE3 C 库无内置测试，需手动验证功能
4. **链接方式**: 生成静态库 `libblake3.a`
