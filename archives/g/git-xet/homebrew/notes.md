# git-xet homebrew 适配笔记

## 编译环境
- 构建系统: Rust (预编译二进制 glibc-dynamic, 需 musl 适配)
- 编译日期: 2026-06-03
- 编译器: N/A (使用 GitHub 预编译二进制)
- 状态: published

## 编译步骤

1. `ohc-run.py init-build git-xet homebrew --url=... --no-download` 初始化编译环境
2. 从 GitHub releases (huggingface/xet-core git-xet-v0.2.1) 下载 `git-xet-linux-aarch64.zip`
3. 预编译二进制为 glibc-dynamic (依赖 libc.so.6/libm.so.6/ld-linux-aarch64.so.1), 无法直接在 musl HarmonyOS 上运行
4. 使用 Alpine gcompat + 自制 shim 庻musl 适配:
   - patchelf --replace-needed: libc.so.6 → libgcompat.so.0
   - patchelf --replace-needed: libm.so.6 → libgcompat.so.0
   - patchelf --replace-needed: ld-linux-aarch64.so.1 → libglibc-shim.so
   - patchelf --set-interpreter /lib/ld-musl-aarch64.so.1
   - 编写 glibc-shim.c 提供缺失符号:
     * pthread_mutexattr_setrobust
     * pthread_mutex_consistent
     * __res_init
     * gnu_get_libc_version
     * __res_state
   - 安装依赖: libgcompat.so.0 (Alpine gcompat), libucontext.so.1, libobstack.so.1, libgcc_s.so.1
5. ELF 篾名 + 验证: git-xet --version → git-xet 0.2.1 ✅

6. `ohc-run.py package` 预编译包制作
7. `ohc-run.py finish git-xet homebrew published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 预编译为 glibc-dynamic | 二进制依赖 libc.so.6/libm.so.6/ld-linux-aarch64.so.1, HarmonyOS 使用 musl libc | 使用 Alpine gcompat 适配层 + 自制 shim 补齐缺失符号 |
| 2 | /lib/ 只读, 无法放置 ld-linux-aarch64.so.1 | 内核只接受系统路径的 interpreter | patchelf --replace-needed 替换 NEEDED 条目 |
| 3 | glibc 特定符号缺失 | pthread_mutexattr_setrobust, pthread_mutex_consistent, __res_init, gnu_get_libc_version | 编写 libglibc-shim.so stub 实现 |
| 4 | gcompat 依赖 libucontext/libobstack | 从 Alpine APK 下载安装 |
| 5 | rustc SIGSEGV 崩溃 | Rust 1.96.0 在 musl 上运行时崩溃 | 无法从源码编译, 使用预编译二进制 |

## 源码修改
- patchelf: --replace-needed libc.so.6→libgcompat.so.0, --replace-needed libm.so.6→libgcompat.so.0, --replace-needed ld-linux-aarch64.so.1→libglibc-shim.so
- patchelf: --set-interpreter /lib/ld-musl-aarch64.so.1
- 自定义: glibc-shim.c (缺失 glibc 符号 stub 实现)

- 无其他源码补丁

## 依赖版本
- Alpine gcompat 1.1.0-r4 (libc6-compat layer)
- Alpine libucontext 1.5.1-r0
- Alpine libobstack 1.2.3 (musl-obstack)
- Alpine libgcc 15.2.0-r5
- OpenSSL 3.5.6 (~/usr/local)
- zlib 1.2.13 (/usr/lib)
- libgcc_s.so.1 (Alpine GCC runtime)

- libglibc-shim.so (自定义 stub)

## 验证结果
```bash
$ LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib:/usr/lib git-xet --version
git-xet 0.2.1
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| git-xet | 9.4MB (stripped) | 预编译+glibc/musl适配二进制 |
| libglibc-shim.so | 18KB | 自定义 glibc 符号 stub |
| libgcompat.so.0 | 75KB | Alpine glibc compat layer |
| libucontext.so.1 | ~6KB | Alpine ucontext |
| libobstack.so.1 | ~5KB | Alpine musl-obstack |
| libgcc_s.so.1 | 202KB | Alpine GCC runtime |
---

**编译结束**: 2026-06-03 15:34
**最终状态**: published
