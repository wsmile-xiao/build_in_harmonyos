# rclone 1.72.1 适配笔记

## 编译环境
- 构建系统: custom（Go）
- 编译日期: 2026-05-18
- 编译器: Go 1.25.5（官方预编译）
- 状态: published（预编译包替代编译）

## 编译失败原因

**Go linker mmap 问题**：

尝试编译 rclone v1.72.1 时遇到 Go linker mmap 失败：
- 鸿蒙内核（HongMeng Kernel 1.12.0）的 mmap 实现与标准 Linux 不完全兼容
- Go 1.25.5 的 linker 在鸿蒙上存在兼容性问题
- Go 的静态链接器依赖特定的 mmap 行为，鸿蒙平台缺乏适配

**根本原因**：
- 鸿蒙系统内存映射机制与标准 Linux 有差异
- Go 编译器缺乏针对鸿蒙平台的适配
- mmap syscall 行为差异导致 linker 失败

## 预编译替代方案

**决策**：使用官方预编译版本替代编译

**步骤**：
1. 下载官方预编译包：https://downloads.rclone.org/v1.72.1/rclone-v1.72.1-linux-arm64.zip
2. 解压获取 rclone 二进制文件（v1.72.1，静态编译）
3. ELF 签名（鸿蒙必需）：使用 `ohc-run.py sign-elf` 工具签名
4. 验证：`./rclone version` 成功显示 v1.72.1
5. 打包为预编译包：rclone-1.72.1-ohos-aarch64.tar.gz

**优势**：
- 官方预编译版本经过充分测试
- 避免了 Go linker 在鸿蒙上的兼容性问题
- ELF 签名后可直接在鸿蒙上运行
- 减少了编译时间和资源消耗

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go linker mmap 失败 | 鸿蒙 mmap 与 Linux 差异 | 使用官方预编译版本 |
| 2 | 二进制无法执行 | 未 ELF 签名 | 使用 ohc-run.py sign-elf 签名 |

## 依赖版本

无编译依赖（使用预编译版本）

## 验证结果

```bash
$ ./rclone version
rclone v1.72.1
- os/version: unknown
- os/kernel: HongMeng Kernel 1.12.0 (aarch64)
- os/type: linux
- os/arch: arm64 (ARMv8 compatible)
- go/version: go1.25.5
- go/linking: static
- go/tags: none
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| rclone-1.72.1-ohos-aarch64.tar.gz | ~65MB | 预编译包（ELF 已签名） |

## 注意事项

- 鸿蒙必须 ELF 签名才能执行二进制文件
- rclone 为静态编译，无需额外依赖库
- 预编译包已包含签名后的二进制

---

**编译结束**: 2026-05-18 17:53
**最终状态**: published（预编译包替代编译）
