# skalibs 2.14.5.1 — OpenHarmony 预编译包说明

## 基本信息
- **名称**: skalibs (Skarnet's library collection)
- **版本**: 2.14.5.1
- **许可证**: ISC
- **作者**: Laurent Bercot (skarnet.org)
- **描述**: skarnet.org 基础库集合，提供低级数据结构、系统工具和实用函数。是 execline/s6 等上层软件的基础依赖。

- **构建系统**: autotools（skalibs 自定义 configure 脚本）
- **目标架构**: aarch64-unknown-linux-ohos
- **编译器**: clang 15.0.4

## 包内容
本预编译包包含以下内容：

### 共享库
- `libskarnet.so.2.14.5.1` (350KB) — 动态链接库
- `libskarnet.so.2.14` → libskarnet.so.2.14.5.1 (soname symlink)
- `libskarnet.so` → libskarnet.so.2.14 (开发 symlink)

### 静态库
- `libskarnet.a` (1.2MB) — 静态归档库

### 头文件 (93个)
位于 `include/skalibs/` 目录下，涵盖所有公开 API：
- 核心工具: alloc.h, buffer.h, bytestr.h, env.h, error.h, sig.h, socket.h
- 数据结构: avltree.h, gensetdyn.h, genqdyn.h, bigkv.h, bitarray.h, cbuffer.h, cdb.h
- 整数序列化: uint16.h, uint32.h, uint64.h
- 时间: tai.h, djbtime.h
- 加密: sha1.h, sha256.h, sha512.h, blake2s.h, stdcrypto.h, crc32c.h
- 网络: ip46.h, socket.h, iopause.h, skaclient.h
- 进程: envexec.h, cspawn.h, child_spawn0.h
- 其他: fmtscan.h, stralloc.h, genalloc.h, siovec.h, selfpipe.h 等

### 系统依赖数据
位于 `lib/skalibs/sysdeps/` 目录下：
- target — 目标平台标识 (aarch64-unknown-linux-ohos)
- sysdeps — 系统能力列表
- socket.lib, pthread.lib, spawn.lib, sysclock.lib, timer.lib, util.lib — 库依赖声明

## 使用方法

### 编译链接
```bash
# 共享库
clang -o myapp myapp.c -I$PREFIX/include -L$PREFIX/lib -lskarnet -Wl,-rpath,$PREFIX/lib

# 静态库
clang -o myapp myapp.c -I$PREFIX/include -L$PREFIX/lib -lskarnet -static
```

### 重要 API 说明
- `env_get()` 已废弃，请使用 `env_get2(environ, key)`
- `bitarray_peek()` 是宏定义（内联），不是函数
- `SHA256Schedule` 是自定义结构体（不是 `SHA256_CTX`）
- `cbuffer_init()` 返回 `int`（0=成功）
- 交叉编译 configure 需要 `--with-sysdep-devurandom=yes`

## 依赖关系
此库是 skarnet.org 软件栈的基础层：
```
skalibs (本库) → s6 → execline → s6-rc → s6-linux-init → s6-portable-utils
```

## 安装路径
- `$PREFIX/lib/libskarnet.so*` — 共享库
- `$PREFIX/lib/libskarnet.a` — 静态库
- `$PREFIX/include/skalibs/` — 头文件
- `$PREFIX/lib/skalibs/sysdeps/` — 系统依赖数据