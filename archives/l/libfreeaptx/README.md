# libfreeaptx

## 软件简介

libfreeaptx 是一个开源的 aptX/aptX HD 音频编解码库实现，提供高质量的音频编解码功能。

**主要功能**：
- aptX 音频编码和解码
- aptX HD 高清音频编码和解码
- 提供共享库和命令行工具

**项目地址**: https://download.savannah.nongnu.org/releases/libfreeaptx/

## 已编译版本

| 版本 | 状态 | 编译日期 | 预编译包 |
|------|------|----------|---------|
| 0.2.2 | published | 2026-06-04 | [libfreeaptx-0.2.2-ohos-aarch64.tar.gz](./0.2.2/packaging/libfreeaptx-0.2.2-ohos-aarch64.tar.gz) |

## 功能特性

- **音频编解码**: 支持标准 aptX 和高清 aptX HD 编解码
- **命令行工具**: 提供 `freeaptxenc` 和 `freeaptxdec` 命令行工具
- **库文件**: 提供 `libfreeaptx.so` 共享库供应用程序调用
- **头文件**: 提供 `freeaptx.h` 头文件用于开发

## 使用方法

### 安装预编译包

```bash
# 通过 cmd-pkgs 安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libfreeaptx 0.2.2
```

### 命令行工具

```bash
# aptX 编码
freeaptxenc < input.raw > output.aptx

# aptX 解码
freeaptxdec < input.aptx > output.raw

# aptX HD 编码
freeaptxenc --hd < input.raw > output.aptxhd

# aptX HD 解码
freeaptxdec --hd < input.aptxhd > output.raw
```

### 库文件链接

```bash
# 编译时链接
clang -o myapp myapp.c -lfreeaptx

# 或使用 pkg-config
clang -o myapp myapp.c $(pkg-config --libs libfreeaptx)
```

## 技术规格

- **构建系统**: Makefile
- **编译器**: clang/clang++
- **依赖**: 仅依赖系统 libc.so
- **架构**: aarch64 (ARM64)
- **平台**: OpenHarmony

## 已知限制

- Makefile 未提供 `make check` 测试目标，功能测试需手动进行
- 输入音频格式要求为 24-bit signed stereo samples

## 版本历史

### 0.2.2 (2026-06-04)
- 首次编译
- 所有功能测试通过
- aptX 和 aptX HD 编解码功能正常

---

*最后更新: 2026-06-05*