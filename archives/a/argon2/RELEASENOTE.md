# Argon2 Release Notes

## 20190702 (2026-04-24)

### 新增
- Argon2 密码哈希算法参考实现
- 支持三种变体: Argon2i, Argon2d, Argon2id
- 命令行工具 argon2
- 静态库 libargon2.a
- 共享库 libargon2.so.1

### 平台适配
- OpenHarmony/OpenClaw aarch64

### 已知限制
- 需设置 KERNEL_NAME=Linux 进行构建
- 无优化的 SIMD 版本（使用 ref.c 实现）

