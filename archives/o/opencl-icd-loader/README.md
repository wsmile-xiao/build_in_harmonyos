# OpenCL ICD Loader

**软件描述**: Khronos OpenCL Installable Client Driver (ICD) Loader - 用于加载和管理 OpenCL 平台实现的标准接口库。

## 概述

OpenCL ICD Loader 是 Khronos Group 提供的标准 OpenCL ICD 加载器，负责：
- 发现系统中安装的 OpenCL 平台（通过 ICD 配置文件）
- 加载 OpenCL 驱动（ICD）
- 提供标准的 OpenCL API 接口

## 已编译版本

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| v2024.05.08 | published | 2026-06-16 | Headers 版本适配（OpenCL 3.0） |

## 功能特性

- ✅ 标准 OpenCL API 支持（OpenCL 1.0-3.0）
- ✅ ICD 发现和加载机制
- ✅ 多平台支持（可同时加载多个 OpenCL 实现）
- ✅ Layer 扩展支持（可选）

## 平台适配要点

### Headers 版本兼容性

**问题**: ICD Loader 源码默认使用 OpenCL 1.2 API，但替换的 Headers 可能是更高版本（如 OpenCL 3.1），导致类型定义冲突。

**解决方案**:
- 修改 `CMakeLists.txt`，将 `CL_TARGET_OPENCL_VERSION` 设置为至少 300（OpenCL 3.0）
- 或使用与 ICD Loader 版本匹配的 Headers

### 已知平台限制

1. **secure_getenv 缺失**: 鸿蒙平台 libc 缺少 `secure_getenv` 函数，ICD Loader 使用回退方案（non-secure getenv），不影响核心功能。

## 使用方法

### 1. 安装预编译包

```bash
# 通过 cmd-pkgs 安装脚本
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- opencl-icd-loader v2024.05.08
```

### 2. 配置 ICD

安装后需要在 `/etc/OpenCL/vendors/` 目录创建 ICD 配置文件（`.icd` 文件），指向实际的 OpenCL 平台实现库。

### 3. 使用 pkg-config

```bash
pkg-config --cflags OpenCL  # 获取编译选项
pkg-config --libs OpenCL    # 获取链接选项
```

## 技术规格

- **构建系统**: CMake
- **编译器**: Clang 15.0.4
- **目标平台**: HarmonyOS (ARM64)
- **依赖**: OpenCL Headers（已内置）
- **产物**: libOpenCL.so（动态库）

## 相关链接

- [GitHub 仓库](https://github.com/KhronosGroup/OpenCL-ICD-Loader)
- [OpenCL 规范](https://www.khronos.org/opencl/)
- [ICD Loader 文档](https://github.com/KhronosGroup/OpenCL-ICD-Loader/blob/main/README.md)

## 许可证

Apache License 2.0

---

**维护者**: AI 编译协作者
**更新日期**: 2026-06-16