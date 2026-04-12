# xz — HarmonyOS aarch64 预编译包

> **一行安装，开箱即用。** 从源码编译，适配鸿蒙系统。

## 快速安装

```bash
tar xzf xz-5.6.2-ohos-aarch64.tar.gz -C ~/usr/local/
~/usr/local/bin/cat --version
```

或使用 install.sh 一键安装：
```bash
sh install-xz-5.6.2.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 5.6.2 | success | 2 |

## 当前版本 (5.6.2) 详情

### 包内容

| 项目 | 数量 |
|------|------|
| 二进制 (bin/) | 未知 个 ELF aarch64，已签名 |
| 手册页 | 未知 个 |
| 主包大小 | 3.5M |

### 编译信息

| 项目 | 值 |
|------|-----|
| 构建系统 | unknown |
| 编译器 | clang + musl libc (HarmonyOS NDK) |
| 目标 | aarch64-unknown-linux-ohos |
| 补丁 | 2 个 |

### 补丁列表
- ✅ 0001-xz-5.6.2.orig-build-aux-config.guess.patch
- ✅ 0002-xz-5.6.2.orig-build-aux-config.sub.patch

## 环境要求

- **平台**: HarmonyOS / OpenHarmony, aarch64
- **依赖**: musl libc（系统自带）

## 许可证

见原始上游源码

---
*由 finalize-archive.sh 自动生成 · 2026-04-09 19:53*
