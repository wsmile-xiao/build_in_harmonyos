# Argon2 - 密码哈希算法参考实现

## 软件简介

Argon2 是密码哈希竞赛（Password Hashing Competition, PHC）的获胜者，是一种现代、安全的密码哈希算法。该软件包提供了 Argon2 的参考实现，包括命令行工具和 C 语言库。

**支持的三种变体**：
- **Argon2d**: 针对 GPU 攻击优化，数据依赖内存访问
- **Argon2i**: 针对侧信道攻击优化，数据独立内存访问
- **Argon2id**: 混合模式，结合 Argon2d 和 Argon2i 的优点

## 编译指导

### 前置依赖

- GCC/Clang 编译器
- GNU Make 构建工具

### HarmonyOS 编译选项

在 HarmonyOS/OpenClaw 平台编译时，需要设置以下环境变量：

```bash
# 设置 KERNEL_NAME 为 Linux（HarmonyOS 内核名不在 Makefile 支持列表中）
export KERNEL_NAME=Linux

# 设置库文件输出目录名
export LIBRARY_REL=lib

# 设置安装前缀
export PREFIX=/path/to/install
```

### 构建命令

```bash
# 编译
make -j1 PREFIX=$PREFIX KERNEL_NAME=Linux LIBRARY_REL=lib

# 测试
make test

# 安装（HarmonyOS 缺少 install 命令，需手动安装）
# 参考 20190702 版本的安装步骤
```

### 已知限制

1. **KERNEL_NAME 不识别**: HarmonyOS 内核名不在 Makefile 支持列表中，需通过 `KERNEL_NAME=Linux` 环境变量强制指定
2. **无 SIMD 优化**: 使用 ref.c 参考实现，未启用 SIMD 指令集优化
3. **install 命令缺失**: HarmonyOS 默认无 install 命令，需手动执行文件复制

## 补丁清单

暂无补丁文件。

## 版本列表

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| [20190702](./20190702/) | ✅ success | 2026-04-24 | 首个成功编译版本 |

## 功能验证

### 命令行工具验证

```bash
# 测试 Argon2i 哈希
echo -n "password" | argon2 somesalt -t 2 -m 16 -p 1 -l 32

# 预期输出
Type:           Argon2i
Iterations:     2
Memory:         65536 KiB
Parallelism:    1
Hash:           c1628832147d9720c5bd1cfd61367078729f6dfb6f8fea9ff98158e0d7816ed0
Encoded:        $argon2i$v=19$m=65536,t=2,p=1$c29tZXNhbHQ$wWKIMhR9lyDFvRz9YTZweHKfbftvj+qf+YFY4NeBbtA
0.128 seconds
Verification ok
```

### 库文件验证

```bash
# 验证静态库
ls -lh lib/libargon2.a
# 预期: lib/libargon2.a (~157KB)

# 验证动态库
ls -lh lib/libargon2.so.1
# 预期: lib/libargon2.so.1 (~113KB)

# 验证头文件
ls -lh include/argon2.h
# 预期: include/argon2.h (存在)
```

## 参考资料

- [Argon2 官方仓库](https://github.com/P-H-C/phc-winner-argon2)
- [Argon2 RFC 9106](https://www.rfc-editor.org/rfc/rfc9106)
- [密码哈希竞赛](https://www.password-hashing.net/)