# b3sum — OpenHarmony 编译档案

## 软件简介
b3sum 是基于 BLAKE3 哈希算法的命令行工具。BLAKE3 是快速、安全的加密哈希算法，支持多线程和 SIMD 加速。

本归档基于 BLAKE3 C 库实现构建简化版 b3sum，支持 OpenHarmony aarch64 平台。

## 功能概述
- 文件/标准输入哈希计算
- 可配置输出长度（-l 参数）
- 静默模式（-q 参数）
- NEON SIMD 加速

## OHOS 适配要点
- 源码取自 BLAKE3 仓库 c/ 子目录
- 需添加 b3sum.c 源码（补丁 0002-b3sum.c.patch）
- 使用 `-DBLAKE3_SIMD_TYPE=neon-intrinsics` 启用 NEON 加速
- 此为简化版实现，非完整 Rust 版本

## 限制
- 不支持 Keyed hash、Derive key、递归目录哈希

## 参考资料
- [BLAKE3 GitHub](https://github.com/BLAKE3-team/BLAKE3)
