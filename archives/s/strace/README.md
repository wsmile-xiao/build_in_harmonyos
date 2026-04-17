# strace 6.19 - HarmonyOS 编译记录

## 概述

strace 是 Linux 系统调用追踪工具，用于监控和诊断进程与内核之间的交互。

**编译状态**: ⚠️ 部分成功（编译通过，运行受限）

## 编译环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS HongMeng Kernel 1.11.0 aarch64 |
| 编译器 | clang 15.0.4 |
| C 库 | musl libc |
| 三元组 | aarch64-unknown-linux-ohos |

## 编译步骤

```bash
# 1. 下载源码
wget --no-check-certificate https://strace.io/files/6.19/strace-6.19.tar.xz
tar xf strace-6.19.tar.xz
cd strace-6.19

# 2. 应用补丁
patch -p1 < patches/0001-add-harmonyos-support-to-config.sub.patch
patch -p1 < patches/0002-fix-unused-function-warning-in-sigreturn.patch

# 3. 配置
mkdir build && cd build
../configure --prefix=$HOME/usr/local --disable-mpers

# 4. 编译（鸿蒙不支持 mkfifo，用单线程）
make -j1

# 5. 安装
make install
```

## 补丁说明

### 0001 - config.sub HarmonyOS 支持

config.guess 已内置 HarmonyOS 识别（`LIBC=ohos`, `*:HarmonyOS:*:*` 模式），
但 config.sub 需要两处额外修改：

1. **三元组解析**：添加 `ohos-linux` → `basic_os=linux-ohos`
2. **内核-OS 组合验证**：在 `linux-gnu* | linux-musl*` 列表中添加 `linux-ohos*`
3. **OS 识别**：在 OS 列表中添加 `ohos*`

### 0002 - 修复未使用函数警告

`sigreturn.c` 中的 `print_sigmask_addr_size` 函数在 **aarch64、arm、x86_64** 等架构上
未被对应的 `arch_sigreturn.c` 引用（只有 i386/m68k/powerpc/s390/sparc 使用了
`tprintsigmask_addr` 宏）。gcc 对 `static inline` 未使用函数不会报错，但
clang 会，加上 `-Werror` 就变成了编译错误。

添加 `__attribute__((unused))` 消除编译错误，这是一个跨架构的 clang 兼容性修复，
不仅限于 HarmonyOS。

## 已知问题

### ptrace 权限被 SELinux 禁止 ⚠️

strace 的核心功能依赖 `ptrace` 系统调用，但鸿蒙系统的 SELinux 策略
（`adhoc_bin` 域）完全禁止了 ptrace 操作：

```
strace echo hello
strace: ptrace(PTRACE_TRACEME, ...): Permission denied
```

**影响**：strace 可以安装但无法执行实际系统调用追踪。

**可能的解决方案**：
- 修改 SELinux 策略添加 ptrace 权限（需要 root）
- 使用开发者模式/调试模式（如有）
- 联系 OpenHarmony 团队获取 ptrace 支持

## 验证结果

| 测试项 | 结果 |
|--------|------|
| strace --version | ✅ PASS |
| 二进制格式检查 | ✅ ELF 64-bit ARM aarch64 |
| strace echo hello | ❌ Permission denied |
| strace -p PID | ❌ Permission denied |
