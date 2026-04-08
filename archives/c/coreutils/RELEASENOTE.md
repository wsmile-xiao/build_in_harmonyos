# coreutils — HarmonyOS aarch64 预编译包

> **一行安装，开箱即用。** 从源码编译，适配鸿蒙系统。

## 快速安装

```bash
tar xzf coreutils-9.10-ohos-aarch64.tar.gz -C ~/usr/local/
~/usr/local/bin/cat --version
```

或使用 install.sh 一键安装：
```bash
sh install-coreutils-9.10.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 9.10 | success#final | 3 |

## 当前版本 (9.10) 详情

### 包内容

| 项目 | 数量 |
|------|------|
| 二进制 (bin/) | 86 个 ELF aarch64，已签名 |
| 手册页 | 100 个 |
| 主包大小 | 11M |

### 排除命令 (14 个)

以下命令因平台限制未包含，请使用系统 **toybox** 替代：

```
ln link unlink realpath readlink ls cp mv rm stat chmod chown chgrp,chroot ,tac 
```

### 编译信息

| 项目 | 值 |
|------|-----|
| 构建系统 | autotools |
| 编译器 | clang + musl libc (HarmonyOS NDK) |
| 目标 | aarch64-unknown-linux-ohos |
| 补丁 | 3 个 |

### 补丁列表
- ✅ 0001-add-harmonyos-support.patch
- ✅ 0002-fix-fstat-for-harmonyos.patch
- ✅ 0003-fix-od-fstat-for-harmonyos.patch

## 环境要求

- **平台**: HarmonyOS / OpenHarmony, aarch64
- **依赖**: musl libc（系统自带）

## 许可证

见原始上游源码

---
*由 finalize-archive.sh 自动生成 · 2026-04-09 02:01*
