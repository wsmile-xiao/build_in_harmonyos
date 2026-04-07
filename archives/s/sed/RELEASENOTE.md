# sed — HarmonyOS aarch64 预编译包

> **一行安装，开箱即用。** 从源码编译，适配鸿蒙系统。

## 快速使用

从 [cmd-pkgs releases](https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases) 下载对应版本的 tar.gz，解压到 ~/usr/local/ 即可使用。

## 可用版本

| 版本 | 状态 | 补丁数 | 质量门禁 |
|------|------|--------|---------|
| 4.9 | success | 2 | PASS |

## 当前版本 (4.9) 详情

### 包含内容

| 内容 | 数量/大小 | 说明 |
|------|----------|------|
| 主二进制 bin/sed | ELF aarch64, 已签名 | 核心程序 |
| Debug 符号包 | 独立下载 | GDB 调试用 |

### 环境要求

- **平台**: HarmonyOS (OpenHarmony) aarch64
- **依赖**: 仅 musl libc（系统自带，无需额外安装）
- **磁盘**: ~416K（解压后）

### 编译信息

| 项目 | 值 |
|------|-----|
| 源码 | https://ftp.gnu.org/gnu/sed/sed-4.9.tar.xz |
| 构建系统 | autotools |
| 编译器 | clang + musl libc |
| 目标 triplet | aarch64-unknown-linux-ohos |
| 补丁数 | 2 个 |
| 质量门禁 | PASS |

### 已知适配

- ✅ 0001-build-aux-config.guess.patch
- ✅ 0002-build-aux-config.sub.patch

### 安装说明

1. 从 releases 页面下载 `sed-4.9-ohos-aarch64.tar.gz`
2. 解压到目标目录: tar xzf <文件> -C ~/usr/local/
3. 修复权限: chmod +x ~/usr/local/bin/*
4. 验证: ${_BIN_NAME} --version → ${VERSION}

> 或使用同目录下的 install.sh 一键安装（支持参数化版本选择）

## 许可证

见原始上游源码（许可证不变）

---
*由 finalize-archive.sh 自动生成 · 2026-04-07 21:51*
