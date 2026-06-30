# LZO2 - 实时数据压缩库

## 简介

LZO2 是一个开源的实时数据压缩库，专注于提供高速的压缩和解压缩功能。它是 LZO 库的第二代版本，由 Markus Franz Xaver Johannes Oberhumer 开发和维护。

## 主要特性

- **高速压缩**: LZO2 设计目标是提供极快的压缩和解压缩速度，适用于需要实时处理的场景
- **低内存占用**: 算法设计注重内存效率，适合嵌入式系统和资源受限环境
- **多种算法**: 提供多个压缩算法变体，支持不同压缩率和速度的平衡
- **开源免费**: 采用 GNU General Public License 发布，可免费使用

## 应用场景

LZO2 广泛应用于：
- 嵌入式系统中的数据压缩
- 实时通信协议的数据压缩（如 OpenVPN）
- 文件系统和存储设备的压缩
- 游戏和多媒体应用的压缩
- 网络传输的数据压缩

## 技术细节

- **最新版本**: 2.10
- **许可协议**: GNU General Public License v2
- **官方网站**: https://www.oberhumer.com/opensource/lzo/
- **源码仓库**: https://github.com/nicholasdavis/lzo2（镜像）

## 鸿蒙平台适配

### 已编译版本
- lzo2 2.10 - aarch64-unknown-linux-ohos

### 适配说明
在鸿蒙平台上编译 LZO2 需要：
1. 应用 config.guess/config.sub 补丁以识别 HarmonyOS 系统
2. 修改 configure 脚本的 umask 设置以适应 HMDFS 文件系统
3. 使用 clang 编译器编译为静态库

### 依赖关系
LZO2 是独立的压缩库，无外部依赖。

---

*文档生成日期: 2026-05-21*
