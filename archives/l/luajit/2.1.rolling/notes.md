# luajit 2.1.rolling 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-05-26
- 编译器: clang
- 状态: built

## 编译步骤

LuaJIT 使用 Makefile 构建系统，编译流程如下：

1. **修复编译器问题**：系统无 gcc，修改 src/Makefile 将 DEFAULT_CC 从 gcc 改为 clang
2. **修复 mremap 问题**：OHOS 不支持 mremap syscall，在 src/lj_alloc.c 中添加 `!defined(__OHOS__)` 条件
3. **修复 /tmp 问题**：/tmp 在 HMDFS 上只读，修改 src/lib_os.c 和 src/lj_trace.c 使用 $TMPDIR 或 /data/local/tmp
4. **编译**：`make PREFIX=$DEFAULT_PREFIX -j4`
5. **安装（DESTDIR模式）**：`make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX`
6. **本地安装**：`make install PREFIX=$DEFAULT_PREFIX`（模拟用户部署）
7. **ELF签名**：对二进制文件进行签名
8. **制作预编译包**：使用 `ohc-run.py package` 制作 tar.gz

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make 失败：gcc 不存在 | LuaJIT 默认使用 gcc，OHOS 系统只有 clang | 修改 src/Makefile: DEFAULT_CC = clang |
| 2 | Unsupported target architecture | Makefile 检测架构失败，因为 TARGET_CC=gcc 不存在 | 修改 DEFAULT_CC 为 clang 后解决 |
| 3 | mremap syscall 不可用 | OHOS 内核不支持 mremap syscall | 在 lj_alloc.c 添加 `#if LJ_TARGET_LINUX && !defined(__OHOS__)` 禁用 |
| 4 | /tmp 只读错误 | HMDFS 上 /tmp 为只读 erofs | 使用 $TMPDIR 或 /data/local/tmp 替代 |
| 5 | sed 权限错误 | ~/usr/local/bin/sed 未签名导致权限拒绝 | 临时修改 PATH 使用系统 sed（toybox） |
| 6 | luajit 权限错误 | 编译的二进制未签名导致无法执行 | 使用 sign-elf 对二进制文件签名 |

## 源码修改

共 4 个补丁：

1. **0001-src-Makefile.patch**
   - 文件：src/Makefile
   - 修改：DEFAULT_CC = gcc → DEFAULT_CC = clang
   - 原因：系统无 gcc，需使用 clang

2. **0002-src-lib_os.c.patch**
   - 文件：src/lib_os.c
   - 修改：os.tmpname() 函数中 /tmp 硬编码
   - 改为：使用 $TMPDIR 或 /data/local/tmp
   - 原因：HMDFS 上 /tmp 只读

3. **0003-src-lj_alloc.c.patch**
   - 文件：src/lj_alloc.c
   - 修改：`#if LJ_TARGET_LINUX` → `#if LJ_TARGET_LINUX && !defined(__OHOS__)`
   - 原因：OHOS 不支持 mremap syscall

4. **0004-src-lj_trace.c.patch**
   - 文件：src/lj_trace.c
   - 修改：perf map 文件路径从 /tmp 改为 $TMPDIR 或 /data/local/tmp
   - 原因：HMDFS 上 /tmp 只读

## 依赖版本

- clang：系统预装
- make：GNU Make 4.4.1

## 验证结果

```bash
# 版本验证
$ ~/usr/local/bin/luajit -v
LuaJIT 2.1.ROLLING -- Copyright (C) 2005-2026 Mike Pall. https://luajit.org/

# 二进制文件检查
$ ls -lh ~/usr/local/bin/luajit-2.1.ROLLING
-rwxrwx--- 1 20001006 file_manager 550K 2026-05-26 12:00 luajit-2.1.ROLLING

# 库文件检查
$ ls -lh ~/usr/local/lib/libluajit-5.1.*
-rw-rw---- 1 20001006 file_manager 840K 2026-05-26 12:00 libluajit-5.1.a
lrwxrwxrwx 1 20001006 file_manager   28 2026-05-26 12:00 libluajit-5.1.so -> libluajit-5.1.so.2.1.ROLLING
lrwxrwxrwx 1 20001006 file_manager   28 2026-05-26 12:00 libluajit-5.1.so.2 -> libluajit-5.1.so.2.1.ROLLING
-rwxrwx--- 1 20001006 file_manager 550K 2026-05-26 12:00 libluajit-5.1.so.2.1.ROLLING
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| luajit-2.1.rolling-ohos-aarch64.tar.gz | 3.9M | 主预编译包 |
| luajit-2.1.rolling-ohos-aarch64-debug.tar.gz | 151K | Debug符号包 |

## 注意事项

1. **编译器适配**：OHOS 系统无 gcc，LuaJIT 必须使用 clang
2. **mremap 禁用**：OHOS 内核不支持 mremap syscall，必须禁用相关功能
3. **临时文件路径**：避免使用 /tmp，改用 $TMPDIR 或 /data/local/tmp
4. **ELF签名**：编译后的二进制文件必须签名才能在 OHOS 上执行
5. **PATH问题**：安装时可能遇到 ~/usr/local/bin/sed 权限问题，需要使用系统 sed
---

**编译结束**: 2026-05-26 12:02
**最终状态**: built
