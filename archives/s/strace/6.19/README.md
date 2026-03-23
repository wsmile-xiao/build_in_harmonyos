# strace 6.19 - HarmonyOS 编译档案

## 概述

strace 是 Linux 下用于跟踪进程系统调用的诊断、调试和指导教学工具。版本 6.19 已在 HarmonyOS HongMeng Kernel 1.11.0 aarch64 环境下成功编译。

**编译状态**: ⚠️ 部分完成（编译成功，运行时受限）

## 编译信息

| 项目 | 值 |
|------|-----|
| 软件版本 | 6.19 |
| 构建系统 | Autotools (configure/make) |
| 目标三元组 | aarch64-unknown-linux-ohos |
| 安装路径 | /storage/Users/currentUser/usr/local |
| 编译日期 | 2026-03-23 |

## 编译步骤

### 1. 下载源码

```bash
cd ~/tmp/opendesk/strace
wget https://github.com/strace/strace/releases/download/v6.19/strace-6.19.tar.xz
tar xf strace-6.19.tar.xz
cd strace-6.19
```

### 2. 应用补丁

需要修改 `build-aux/config.guess` 和 `build-aux/config.sub` 以支持 HarmonyOS：

```bash
# 补丁 1: config.guess - 添加 HarmonyOS 系统识别
patch -p1 < patches/0001-adapt-config.guess-for-harmonyos.patch

# 补丁 2: config.sub - 添加 linux-ohos 三元组支持
patch -p1 < patches/0002-adapt-config.sub-for-harmonyos.patch

# 补丁 3: sigreturn.c - 修复 clang 未使用函数警告
patch -p1 < patches/0003-fix-unused-function-warning-for-ohos-clang.patch
```

### 3. 配置

```bash
export TMPDIR=$HOME/tmp
./configure \
    --host=aarch64-unknown-linux-ohos \
    --prefix=/storage/Users/currentUser/usr/local \
    --disable-mpers
```

**关键参数说明**:
- `--host=aarch64-unknown-linux-ohos`: 交叉编译目标三元组，让 configure 识别为 Linux 兼容系统
- `--disable-mpers`: 禁用 m32 personality 支持，鸿蒙系统没有 32 位程序兼容层，不使用此参数会导致编译错误

### 4. 编译和安装

```bash
make -j$(nproc)
make install
```

## 鸿蒙适配说明

### config.guess 修改（3 处）

1. **case 匹配扩展**: 在 `UNAME_SYSTEM` 的 case 语句中添加 `HarmonyOS`，使其进入 Linux 兼容分支
2. **LIBC 检测**: 添加 `__OHOS__` 宏识别，将 LIBC 设为 `ohos`（最终三元组输出为 `aarch64-unknown-linux-ohos`）
3. **系统识别逻辑**: 添加 `*:HarmonyOS:*:*` 匹配分支，输出 `aarch64-unknown-linux-$LIBC`

### config.sub 修改（2 处）

1. **basic machine-OS 组合**: 添加 `ohos-linux` 映射，将 `basic_os` 设为 `linux-ohos`
2. **kernel-os 验证**: 在 `linux-*` kernel-os case 语句中添加 `linux-ohos*`

## 已知限制

### 🔴 PTRACE 无法使用

strace 的核心功能依赖 `ptrace` 系统调用，但 HarmonyOS 的 SELinux 策略禁止了用户空间的 ptrace 访问：

```
$ strace ls
strace: test_ptrace_setoptions_follow: PTRACE_TRACEME: Permission denied
```

这意味着虽然二进制文件编译正确，但无法实际用于追踪系统调用。这是 HarmonyOS 内核安全策略的限制，无法通过用户空间的修改解决。

## 测试结果

| 测试项 | 结果 | 说明 |
|--------|------|------|
| strace --version | ✅ 通过 | 正确输出版本信息 strace --version 6.19 |
| strace ls (ptrace 追踪) | ❌ 失败 | PTRACE_TRACEME: Permission denied |

详细测试报告见 [reports/test-report.md](reports/test-report.md)。

## 文件结构

```
archives/s/strace/6.19/
├── README.md                              # 本文件
├── manifest.yaml                          # 编译元数据
├── patches/
│   ├── 0001-adapt-config.guess-for-harmonyos.patch
│   └── 0002-adapt-config.sub-for-harmonyos.patch
├── reports/
│   └── test-report.md                     # 测试报告
└── logs/
    └── (编译日志)
```

## 参考

- [strace 官网](https://strace.io/)
- [strace 6.19 发布说明](https://github.com/strace/strace/releases/tag/v6.19)
- [strace 源码仓库](https://github.com/strace/strace)
strace 官网](https://strace.io/)
- [strace 6.19 发布说明](https://github.com/strace/strace/releases/tag/v6.19)
- [strace 源码仓库](https://github.com/strace/strace)
