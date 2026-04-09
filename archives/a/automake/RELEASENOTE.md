# automake — HarmonyOS aarch64 预编译包

> **一行安装，开箱即用。** 从源码编译，适配鸿蒙系统。

## 快速安装

```bash
tar xzf automake-1.16.5-ohos-aarch64.tar.gz -C ~/usr/local/
~/usr/local/bin/automake --version
```

或使用 install.sh 一键安装：
```bash
sh install-automake-1.16.5.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.16.5 | success | 1 |

## 当前版本 (1.16.5) 详情

### 包内容

| 项目 | 数量 | 说明 |
|------|------|------|
| 脚本 (bin/) | 4 个 (automake, aclocal, +版本化副本) | Perl 脚本，非 ELF |
| Perl 模块 | Automake/*.pm | Config.pm 等核心模块 |
| M4 宏 | aclocal-1.16/*.m4 | 含 internal 子目录 |
| Automake 模板 | automake-1.16/am/*.am | Makefile 构建模板 |
| 辅助脚本 | compile, install-sh, missing 等 9 个 | 安装到 pkgvdatadir |
| 主包大小 | 1.2M | 105 个文件 |

### 编译信息

| 项目 | 值 |
|------|-----|
| 构建系统 | autotools (configure) + gen-all.pl (手动生成) |
| 编译器 | clang + musl libc (HarmonyOS NDK) |
| 目标 | aarch64-unknown-linux-ohos |
| Perl | /data/service/hnp/bin/perl (v5.42.0) |
| 补丁 | 1 个（config.guess + config.sub） |

### 补丁列表
- ✅ `0001-port-for-ohos.patch` — 完整 HarmonyOS 适配：
  - **config.guess**: HarmonyOS 内核检测 (`HarmonyOS)` + aarch64 输出 (`linux-ohos`) + 同步上游新版改进
  - **config.sub** (3 处): OS 识别列表添加 `linux-ohos*` / `ohos*`；kernel-OS 解码添加 `linux-ohos*` → kernel=linux, os=ohos；kernel-OS 验证添加合法组合

## 环境要求

- **平台**: HarmonyOS / OpenHarmony, aarch64
- **依赖**:
  - Perl 5.006+ （运行时必需）
  - Autoconf 2.72+ （配合使用）
  - GNU Make 4.x （构建 Autotools 项目时）
  - musl libc（系统自带）

## 已知限制

1. **官方测试套件不可用** — `make check` 触发 automake 自身重新生成，因鸡生蛋问题失败
2. **make install 不可用** — 同上原因，需手动安装或使用 install.sh
3. **纯 Perl 项目** — 无 ELF 二进制，RPATH / 签名等检查不适用

## 许可证

GPLv2+ （见原始上游源码）

---
*信息矫正: 2026-04-09 — 补丁已纳入 config.sub 修复，shebang 已改为 /bin/env perl，所有归档信息同步更新*
