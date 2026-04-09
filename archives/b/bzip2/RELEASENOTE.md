# bzip2 — HarmonyOS aarch64 预编译包

> **一行安装，开箱即用。** 从源码编译，适配鸿蒙系统。

## 快速安装

```bash
tar xzf bzip2-1.0.8-ohos-aarch64.tar.gz -C ~/usr/local/
~/usr/local/bin/cat --version
```

或使用 install.sh 一键安装：
```bash
sh install-bzip2-1.0.8.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.0.8 | success | 1 |

## 当前版本 (1.0.8) 详情

### 包内容

| 项目 | 数量 |
|------|------|
| 二进制 (bin/) | 未知 个 ELF aarch64，已签名 |
| 手册页 | 未知 个 |
| 主包大小 | 820K |

### 编译信息

| 项目 | 值 |
|------|-----|
| 构建系统 | makefile |
| 编译器 | clang + musl libc (HarmonyOS NDK) |
| 目标 | aarch64-unknown-linux-ohos |
| 补丁 | 1 个 |

### 补丁列表
- ✅ 0001-bzip2-1.0.8.orig-Makefile.patch

## 环境要求

- **平台**: HarmonyOS / OpenHarmony, aarch64
- **依赖**: musl libc（系统自带）

## 许可证

见原始上游源码

---
*由 finalize-archive.sh 自动生成 · 2026-04-09 19:08*
