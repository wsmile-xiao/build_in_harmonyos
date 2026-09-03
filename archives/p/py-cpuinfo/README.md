# py-cpuinfo

**Get CPU info with pure Python**

## 简介

py-cpuinfo 是一个纯 Python 库，用于获取 CPU 信息（架构、品牌、频率、特性等），无需编译 C/C++ 扩展。支持 Linux、Windows、macOS、BSD、Solaris 等主流平台。

## 特性

- 纯 Python 实现，跨平台
- 获取 CPU 架构、位数、核心数、品牌、频率等详细信息
- 提供 Python API (`cpuinfo.get_cpu_info()`) 和命令行工具 (`cpuinfo`)
- 支持 x86_64、ARM、RISC-V 等多种架构

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 9.0.0 | ✅ 已适配 | 纯 Python，无需编译 |

## 上游信息

- **官方仓库**: https://github.com/workhorsy/py-cpuinfo
- **许可证**: MIT
- **语言**: Python 3

## 使用方式

### Python API
```python
import cpuinfo
info = cpuinfo.get_cpu_info()
print(info['brand_raw'])  # CPU 品牌
print(info['arch'])       # 架构（如 ARM_8）
print(info['count'])      # 核心数
```

### 命令行
```bash
cpuinfo
```

## 依赖

- Python 3.x
- setuptools（构建时）

## 适配说明

HarmonyOS aarch64 平台兼容 Linux 系统调用，py-cpuinfo 可直接读取 `/proc/cpuinfo` 和使用 `lscpu` 获取 CPU 信息。适配补丁仅修改上游测试辅助函数，使其识别 HarmonyOS 平台并映射到 Linux 分支。

## 维护者

AtomCode AI
