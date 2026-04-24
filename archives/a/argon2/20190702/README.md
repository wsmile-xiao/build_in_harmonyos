# Argon2 20190702

## 版本信息

- **软件**: Argon2 Password Hashing Reference Implementation
- **版本**: 20190702
- **发布日期**: 2019-07-02
- **编译日期**: 2026-04-24
- **编译状态**: ✅ success
- **构建系统**: Makefile

## 编译详情

### 构建命令

```bash
make -j1 PREFIX=$HOME/usr/local KERNEL_NAME=Linux LIBRARY_REL=lib
```

### 构建参数

- `KERNEL_NAME=Linux`: 强制指定内核名称（HarmonyOS 不在支持列表中）
- `LIBRARY_REL=lib`: 设置库文件输出目录名
- `-j1`: 单线程编译（避免并行编译问题）

### 测试结果

执行 `make test` 命令，所有测试通过：

- Argon2i v=16: OK
- Argon2d v=16: OK
- Argon2id v=16: OK
- Argon2i v=19: OK
- Argon2d v=19: OK
- Argon2id v=19: OK
- 所有 hash 测试: PASS
- 错误状态测试: PASS

### 功能验证

```bash
$ echo -n "password" | argon2 somesalt -t 2 -m 16 -p 1 -l 32
Type:           Argon2i
Iterations:     2
Memory:         65536 KiB
Parallelism:    1
Hash:           c1628832147d9720c5bd1cfd61367078729f6dfb6f8fea9ff98158e0d7816ed0
Encoded:        $argon2i$v=19$m=65536,t=2,p=1$c29tZXNhbHQ$wWKIMhR9lyDFvRz9YTZweHKfbftvj+qf+YFY4NeBbtA
0.128 seconds
Verification ok
```

## 安装文件清单

### 可执行文件

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/argon2 | 129KB | Argon2 命令行工具 |

### 库文件

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libargon2.a | 157KB | 静态链接库 |
| lib/libargon2.so.1 | 113KB | 动态链接库 |
| lib/libargon2.so | - | 符号链接 → libargon2.so.1 |

### 头文件和配置

| 文件 | 说明 |
|------|------|
| include/argon2.h | C 语言头文件 |
| lib/pkgconfig/libargon2.pc | pkg-config 配置文件 |

## 遇到的问题及解决方案

### 1. 网络下载超时

**问题**: GitHub wget 下载源码超时  
**解决**: 使用 git clone 替代 wget 下载  
**命令**: `git clone --branch 20190702 https://github.com/P-H-C/phc-winner-argon2.git`

### 2. KERNEL_NAME 不识别

**问题**: HarmonyOS 内核名不在 Makefile 支持列表中  
**解决**: 设置 `KERNEL_NAME=Linux` 环境变量强制指定  
**原因**: Makefile 仅支持 Linux、Darwin、FreeBSD、OpenBSD 等，不识别 HarmonyOS

### 3. install 命令缺失

**问题**: HarmonyOS 无 install 命令，导致 `make install` 失败  
**解决**: 手动执行文件复制步骤  
**替代方案**: 使用 cp、mkdir 等基础命令手动安装文件

### 4. bash 路径问题

**问题**: install.sh 使用 `#!/bin/bash`，但 HarmonyOS 默认无此路径  
**解决**: 使用 `/data/service/hnp/bin/bash` 替代  
**备注**: HarmonyOS bash 位于 `/data/service/hnp/bin/bash`

## 已知限制

1. **无 SIMD 优化**: 使用 ref.c 参考实现，未启用 SIMD 指令集优化
2. **需要手动安装**: install 命令不可用，需手动复制文件
3. **网络依赖**: 从 GitHub 下载源码可能超时

## 相关文档

- [编译进度](./PROGRESS.md) - 详细的编译过程记录
- [测试报告](./reports/test-report.md) - 完整的测试输出
- [质量报告](./reports/quality-report.md) - 质量门禁验证结果
- [构建日志](./reports/build.log) - 构建过程日志
- [安装日志](./reports/staging-install.log) - 安装过程日志

## 预编译包

- `argon2-20190702-ohos-aarch64.tar.gz` (527KB) - 预编译安装包
- `debug.tar.gz` (12KB) - 调试信息包

## 源码信息

- **源码地址**: https://github.com/P-H-C/phc-winner-argon2/archive/refs/tags/20190702.tar.gz
- **压缩格式**: tar.gz