# strace 6.19 - 编译报告

> **编译日期**: 2026-03-23  
> **编译环境**: HarmonyOS HongMeng Kernel 1.11.0 aarch64  
> **编译器**: clang 15.0.4  
> **C 库**: musl libc  

## 编译配置

```bash
export TMPDIR=$HOME/tmp
export CC=clang
export DEFAULT_PREFIX=$HOME/usr/local

# 下载源码
wget --no-check-certificate https://strace.io/files/6.19/strace-6.19.tar.xz
tar xf strace-6.19.tar.xz
cd strace-6.19

# 应用补丁
patch -p1 < 0001-add-harmonyos-support-to-config.sub.patch
patch -p1 < 0002-fix-unused-function-warning-in-sigreturn.patch

# 配置（禁用多架构 personality 支持）
mkdir build && cd build
../configure --prefix=$DEFAULT_PREFIX --disable-mpers

# 编译（单线程，鸿蒙不支持 mkfifo/jobserver）
make -j1

# 安装
make install
```

## 编译过程

### Phase 1: config.guess/config.sub 适配

- **config.guess**: strace 6.19 内置了 HarmonyOS 识别（`LIBC=ohos`, `*:HarmonyOS:*:*` 模式），无需修改
- **config.sub**: 需要两处修改：
  1. 添加 `ohos-linux` 三元组解析（`basic_os=linux-ohos`）
  2. 在 `linux-gnu* | linux-musl*` 列表中添加 `linux-ohos*` 以通过内核-OS 组合验证

### Phase 2: configure

- 平台识别为 `aarch64-unknown-linux-ohos` ✅
- `--disable-mpers` 禁用了 m32 personality 支持（鸿蒙不需要追踪 32 位程序）

### Phase 3: 编译问题

- **sigreturn.c 编译错误**: `print_sigmask_addr_size` 在 aarch64 架构上未被引用，clang `-Werror` 报错
  - 修复：添加 `__attribute__((unused))`
  - 这是跨架构的 clang 兼容性问题，不仅限于 HarmonyOS

## 编译产物

| 文件 | 路径 | 大小 |
|------|------|------|
| strace | $HOME/usr/local/bin/strace | 1.9 MB |
| strace-log-merge | $HOME/usr/local/bin/strace-log-merge | 1.9 KB |
| man pages | $HOME/usr/local/share/man/man1/ | — |

## 已知限制

- ptrace 系统调用被 SELinux 策略禁止，strace 无法执行实际追踪
- 详见 test-report.md
