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
| 补丁数 | 10 个 |
| 配置参数 | `--with-internal-glib` |
| 上游测试 | `make check` → 30/30 通过 |
| 质量门禁 | 见 RELEASENOTE |

## 平台适配原因

### 为什么需要补丁

pkg-config 内嵌了一个完整的 glib 2.56.0 子目录，因此需要同时修复主目录和 glib 子目录的构建文件：

| # | 文件 | 原因 | 改动 |
|---|------|------|------|
| 1 | `config.guess` | 标准 GNU config.guess 不识别 HarmonyOS 平台 | 新增 `*:HarmonyOS:*:*)` 分支，映射到 `aarch64-unknown-linux-ohos` |
| 2 | `config.sub` | 同上，新增 ohos OS 条目 | 新增 `ohos* \| linux-ohos*` OS 匹配 |
| 3 | `configure` | conftest 执行在 musl 下需兜底 | `./conftest$ac_exeext` 改为 `./conftest$ac_exeext \| cat` |
| 4 | `glib/config.guess` | glib 子目录有独立的 config.guess 副本 | 与 #1 相同修改 |
| 5 | `glib/config.sub` | glib 子目录有独立的 config.sub 副本 | 与 #2 相同修改 |
| 6 | `glib/configure` | glib 子目录的 conftest 执行 | 与 #3 相同修改 |
| 7 | `configure` | **HMDFS 文件系统限制**：configure 生成的 config.status 用 `umask 077` 创建临时目录，产生的 `drwx--S---` 权限在 HMDFS 下连属主都不可写，报 `can't create ./confXXX/subs1.awk: Permission denied` | `umask 077` → `umask 022` |
| 8 | `glib/configure` | 同 #7（glib 子目录独立副本） | `umask 077` → `umask 022` |
| 9 | `glib/configure` | 旧版 glib 2.56.0 的 `gatomic.c` 在 aarch64+clang 下把 `gsize` 传给指针参数，4 处 `-Wint-conversion` 被 `-Werror` 升级为错误 | 在探测的编译警告列表追加 `-Wno-error=int-conversion -Wno-error=incompatible-pointer-types` |
| 10 | `Makefile.in` | **HMDFS 文件系统限制**：`install-exec-hook` 用 `ln -f` 创建 triplet 前缀硬链接，HMDFS 不允许，报 `ln: cannot create hard link ...: Operation not permitted` | 改用 wrapper 脚本（`exec pkg-config "$@"`）替代硬链接 |

### 技术债务

- **#9 的警告抑制** 是技术债务（vendor 代码不应修改，且只是掩盖而非修复类型问题），但旧版 glib 2.56.0 在 aarch64+clang 下必须如此。升级 pkg-config 到使用系统 glib 的更新版本可消除。

## 已知限制

1. **HMDFS 限制**：triplet wrapper (`aarch64-unknown-linux-ohos-pkg-config`) 使用脚本而非硬链接/软链接
2. **内嵌 glib**：pkg-config 0.29.2 内嵌了完整 glib 2.56.0，体积较大（约 654KB）

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
