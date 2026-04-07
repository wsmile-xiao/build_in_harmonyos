# pkg-config 0.29.2 — HarmonyOS aarch64 编译适配说明

> **pkg-config 用于在编译时获取库的编译和链接参数。** 从源码编译，适配鸿蒙系统。

## 软件简介

pkg-config 是一个辅助工具，用于查询已安装库的编译标志（CFLAGS）和链接标志（LIBS）。许多 autotools 构建的软件依赖它来查找依赖库。

## 编译信息

| 项目 | 值 |
|------|-----|
| 源码 | [pkg-config 0.29.2](https://pkg-config.freedesktop.org/releases/) |
| 构建系统 | autotools（内嵌 glib 2.56.0） |
| 编译器 | clang + musl libc |
| 目标 triplet | `aarch64-unknown-linux-ohos` |
| 补丁数 | 6 个 |
| 质量门禁 | 见 RELEASENOTE |

## 平台适配原因

### 为什么需要补丁

pkg-config 内嵌了一个完整的 glib 2.56.0 子目录，因此需要同时修复主目录和 glib 子目录的构建文件：

| # | 文件 | 原因 | 改动 |
|---|------|------|------|
| 1 | `config.guess` | 标准 GNU config.guess 不识别 HarmonyOS 平台 | 新增 `*:HarmonyOS:*:*)` 分支，映射到 `aarch64-unknown-linux-ohos` |
| 2 | `config.sub` | 同上，新增 ohos OS 条目 | 新增 `ohos* \| linux-ohos*` OS 匹配 |
| 3 | `glib/config.guess` | glib 子目录有独立的 config.guess 副本 | 与 #1 相同修改 |
| 4 | `glib/config.sub` | glib 子目录有独立的 config.sub 副本 | 与 #2 相同修改 |
| 5 | `configure` (glib) | conftest pipe 兼容 musl libc | 修复 `\| cat` 被 shell 管道截断的问题 |
| 6 | `glib/glib/Makefile` | gatomic.c 类型警告被 -Werror 升级为错误 | 追加 `-Wno-error=int-conversion -Wno-error=incompatible-pointer-types` |

### 技术债务

- **P3 的 Makefile 修改** 是技术债务（vendor 代码不应修改），但旧版 glib 2.56.0 在 aarch64+clang 下必须如此。升级 pkg-config 到更新版本（使用系统 glib）可消除此债务。

## 已知限制

1. **无 .pc 文件**：当前安装不含 .pc 文件（pkg-config 自身不需要，依赖它的软件需要时自行生成）
2. **HMDFS 软链接限制**：triplet wrapper (`aarch64-unknown-linux-ohos-pkg-config`) 使用脚本而非软链接
3. **内嵌 glib**：pkg-config 0.29.2 内嵌了完整 glib 2.56.0，体积较大（674KB）

## 验证方法

```bash
# 版本检查
pkg-config --version          # → 0.29.2

# 功能测试（查询自身）
pkg-config --modversion pkg-config  # → 0.29.2

# Wrapper 脚本可用性
aarch64-unknown-linux-ohos-pkg-config --version  # → 0.29.2
```

## 编译命令参考

```bash
./configure --prefix=$PREFIX && make && make install
```
零额外参数即可编译通过。

## 许可证

[GPL-2.0-or-later](https://gitlab.freedesktop.org/pkg-config/pkg-config/-/blob/master/COPYING)（原始上游许可证不变）
