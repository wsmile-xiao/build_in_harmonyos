# qsv homebrew 适配笔记

## 编译环境
- 构建系统: Rust (预编译二进制 glibc-dynamic, 需 gcompat 适配)
- 编译日期: 2026-06-03
- 编译器: N/A (使用 GitHub 预编译二进制)
- 状态: built

## 编译步骤

1. 从 GitHub releases (dathere/qsv 20.1.0) 下载 `qsv-20.1.0-aarch64-unknown-linux-gnu.zip`
2. 预编译二进制为 glibc-dynamic (依赖 libc.so.6/libm.so.6/libpthread.so.0/libdl.so.2/ld-linux-aarch64.so.1/libgcc_s.so.1)
3. 使用 Alpine gcompat + 自制 shim 庻musl 适配（复用 git-xet 的成功方案）:
   - patchelf --replace-needed: libc.so.6 → libgcompat.so.0
   - patchelf --replace-needed: libm.so.6 → libgcompat.so.0
   - patchelf --replace-needed: libpthread.so.0 → libgcompat.so.0
   - patchelf --replace-needed: libdl.so.2 → libgcompat.so.0
   - patchelf --replace-needed: ld-linux-aarch64.so.1 → libglibc-shim.so
   - patchelf --set-interpreter /lib/ld-musl-aarch64.so.1
   - patchelf --set-rpath ~/usr/local/lib
4. ELF 签名所有二进制和库
5. 验证: qsv --version → qsv 20.1.0 ✅, qsvlite --version → ✅, qsvdp --version → ✅
6. 功能测试: qsv stats, qsv count 正常工作 ✅

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 预编译为 glibc-dynamic | 二进制依赖 libc.so.6 等, HarmonyOS 使用 musl libc | 使用 Alpine gcompat 适配层 + 自制 shim (复用 git-xet 方案) |
| 2 | 无 musl 静态二进制可用 | qsv 项目不发布 aarch64-linux-musl 版本 | 使用 glibc-dynamic + gcompat 方案 |
| 3 | init-build 超时/下载失败 | GitHub 网络不稳定 | 使用 ghfast.top 镜像下载 |
| 4 | unzip 不支持 PK v4.5 | toybox unzip 不支持新版 zip 格式 | 使用 Python zipfile 模块解压 |

## 源码修改
- patchelf: --replace-needed libc.so.6→libgcompat.so.0, --replace-needed libm.so.6→libgcompat.so.0, --replace-needed libpthread.so.0→libgcompat.so.0, --replace-needed libdl.so.2→libgcompat.so.0
- patchelf: --replace-needed ld-linux-aarch64.so.1→libglibc-shim.so
- patchelf: --set-interpreter /lib/ld-musl-aarch64.so.1
- patchelf: --set-rpath ~/usr/local/lib

- 无其他源码补丁

## 依赖版本
- Alpine gcompat 1.1.0-r4 (libc6-compat layer)
- Alpine libucontext 1.5.1-r0
- Alpine libobstack 1.2.3 (musl-obstack)
- Alpine libgcc 15.2.0-r5
- libgcc_s.so.1 (Alpine GCC runtime)
- libglibc-shim.so (自定义 stub, 复用 git-xet 构建)

## 验证结果
```bash
$ LD_LIBRARY_PATH=~/usr/local/lib:/usr/lib qsv --version
qsv 20.1.0-jemalloc-apply;fetch;foreach;self_update-16-16;18.64 GiB-46.60 GiB-7.04 GiB-23.30 GiB (aarch64-unknown-linux-gnu compiled with Rust 1.95;Linux-Linux HongMeng Kernel 1.12.0;-16) compiled

$ LD_LIBRARY_PATH=~/usr/local/lib:/usr/lib qsvlite --version
qsvlite 20.1.0-jemalloc-self_update-16-16;18.64 GiB-46.60 GiB-7.06 GiB-23.30 GiB (aarch64-unknown-linux-gnu compiled with Rust 1.95;Linux-Linux HongMeng Kernel 1.12.0;-16) compiled

$ LD_LIBRARY_PATH=~/usr/local/lib:/usr/lib qsvdp --version
qsvdp 20.1.0-jemalloc-geocode;self_update-16-16;18.64 GiB-46.60 GiB-7.05 GiB-23.30 GiB (aarch64-unknown-linux-gnu compiled with Rust 1.95;Linux-Linux HongMeng Kernel 1.12.0;-16) compiled
```

功能测试:
```bash
$ qsv stats test.csv  # 正常输出统计信息 ✅
$ qsv count test.csv  # 正确计数 ✅
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| qsv | 33MB (stripped) | 全功能版预编译+glibc/musl适配二进制 |
| qsvlite | 23MB (stripped) | 精简版预编译+glibc/musl适配二进制 |
| qsvdp | 22MB (stripped) | DataPusher版预编译+glibc/musl适配二进制 |
| libglibc-shim.so | 18KB | 自定义 glibc 符号 stub (复用 git-xet) |
| libgcompat.so.0 | 75KB | Alpine glibc compat layer (复用 git-xet) |
| libucontext.so.1 | ~75KB | Alpine ucontext (复用 git-xet) |
| libobstack.so.1 | ~75KB | Alpine musl-obstack (复用 git-xet) |
| libgcc_s.so.1 | 141KB | Alpine GCC runtime (复用 git-xet) |
---

**编译结束**: 2026-06-03 16:00
**最终状态**: built
