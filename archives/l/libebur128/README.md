# libebur128

libebur128 is a library implementing the EBU R128 loudness standard for audio loudness measurement.

- **Homepage**: https://github.com/jiixyj/libebur128
- **Category**: audio/loudness
- **License**: MIT
- **Versions**: 1.2.6

## 功能概述

libebur128 实现了 EBU R128 响度标准，提供以下核心功能：

- 全局响度测量 (Integrated Loudness, LUFS)
- 短期响度 (Short-term Loudness)
- 瞬间响度 (Momentary Loudness)
- 响度范围 (Loudness Range, LRA)
- 样本峰值检测 (Sample Peak)
- 真峰值检测 (True Peak)
- 相对阈值 (Relative Threshold)

支持多种音频数据格式 (short/int/float/double)，支持多种声道配置（单声道、立体声、5.1 等）。

## 鸿蒙平台适配说明

- 构建系统: CMake
- 补丁: 2 个（cmake_minimum_required 版本兼容性修复，CMake 4.x 要求 >= 3.5）
- 无外部依赖（纯 C 库，仅依赖 libc）
- 预编译包: libebur128-1.2.6-ohos-aarch64.tar.gz (stripped, ELF-signed)
- 功能测试: 43/43 通过，验证库在鸿蒙平台功能正常

## 安装验证

```bash
# pkg-config 验证
PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig pkg-config --modversion libebur128
# 输出: 1.2.6

# 编译链接验证
cc -o test test.c -I~/usr/local/include -L~/usr/local/lib -lebur128 -lm