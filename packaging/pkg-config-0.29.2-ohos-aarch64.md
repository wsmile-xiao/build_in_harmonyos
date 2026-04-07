# pkg-config 0.29.2 — HarmonyOS aarch64 预编译包

> **一行安装，开箱即用。** 从源码编译，适配鸿蒙系统。

## 快速使用

```bash
# 1. 解压
tar xzf pkg-config-0.29.2-ohos-aarch64.tar.gz -C ~/usr/

# 2. 修复权限（鸿蒙签名机制要求）
chmod +x ~/usr/pkg-config-0.29.2-ohos-aarch64/bin/*

# 3. 激活
. ~/usr/pkg-config-0.29.2-ohos-aarch64/activate.sh

# 4. 验证
pkg-config --version    # → 0.29.2
```

## 包含内容

| 内容 | 数量/大小 | 说明 |
|------|----------|------|
| 主二进制 `bin/pkg-config` | 674 KB (ELF aarch64, 已签名) | 核心程序 |
| Triplet wrapper | 64 B | `aarch64-unknown-linux-ohos-pkg-config` |
| `.pc` 文件 | 21 个 | zlib / openssl / ncursesw / python3 等 |
| aclocal m4 宏 | 6 个 | autotools 项目可用 |
| man page | 1 个 | `pkg-config(1)` |
| Debug 符号 | 128 KB (独立包) | GDB 调试用，按需下载 |

## 环境要求

- **平台**: HarmonyOS (OpenHarmony) aarch64
- **依赖**: 仅 musl libc（系统自带，无需额外安装）
- **磁盘**: ~1.5 MB（解压后）

## 编译信息

| 项目 | 值 |
|------|-----|
| 源码 | [pkg-config 0.29.2](https://pkg-config.freedesktop.org/releases/) |
| 构建系统 | autotools (内嵌 glib 2.56.0) |
| 编译器 | clang + musl libc |
| 目标 triplet | `aarch64-unknown-linux-ohos` |
| 补丁数 | 6 (config.guess ohos 识别 / conftest pipe 修复) |
| 质量门禁 | ✅ PASS (G1-G4 全部通过) |

## 已知适配

- ✅ config.guess / config.sub 添加 HarmonyOS 平台识别
- ✅ glib 子目录同步适配
- ✅ conftest pipe 修复（musl 兼容）
- ✅ glib gatomic.c 类型警告抑制（vendor 代码）
- ✅ HMDFS 软链接限制 → wrapper 脚本替代

## 许可证

[GPL-2.0-or-later](https://gitlab.freedesktop.org/pkg-config/pkg-config/-/blob/master/COPYING)（原始上游许可证不变）
