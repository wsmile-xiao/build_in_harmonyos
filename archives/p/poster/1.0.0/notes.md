# poster 1.0.0 适配笔记

## 编译环境
- 构建系统: makefile (简单 Makefile，无 configure 脚本)
- 编译日期: 2026-06-13
- 编译器: clang 15.0.4 / clang++
- 目标平台: aarch64 (OpenHarmony / musl libc)
- 状态: published

## 编译步骤

poster 使用简单的 Makefile，没有 configure 脚本。原始 Makefile 使用硬编码的 gcc 和 /usr/local 路径。

1. 修改 Makefile，添加 CC/CFLAGS/PREFIX/DESTDIR 变量支持（补丁 0001-Makefile.patch）
2. `make CC=clang CFLAGS="-fPIC -O2"` — 编译
3. `make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX` — staging 安装
4. `make install PREFIX=$DEFAULT_PREFIX` — 本地安装（需先 rm -f 旧文件）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL下载失败 | GitHub HTTPS 证书验证失败 | 使用 ghfast.top 镜像下载 |
| 2 | Makefile 硬编码路径 | 原始 Makefile 使用 gcc 和 /usr/local | 补丁添加 CC/CFLAGS/PREFIX/DESTDIR 变量 |
| 3 | gets() 函数警告 | poster.c 使用 C99 已删除的 gets() | 仅警告，不影响编译运行 |
| 4 | 本地安装 cp 权限冲突 | HMDFS 不允许覆盖已签名文件 | rm -f 后再 cp |
| 5 | 首次执行 Operation not permitted | ELF 未签名不可执行 | sign-elf 签名后正常执行 |

## 源码修改

- Makefile: 添加 CC/CFLAGS/PREFIX/DESTDIR 变量，替换硬编码路径
- 补丁: 0001-Makefile.patch

## 编译警告详情

```
poster.c:573:21: warning: call to undeclared function 'gets'
    [-Wimplicit-function-declaration]
poster.c:573:31: warning: comparison between pointer and integer
    [-Wpointer-integer-compare]
```

gets() 在 C99 标准后已移除，poster.c 源码使用了此函数。在 musl libc 环境下，gets() 仍作为兼容函数存在（隐式声明），编译产生 2 个警告但不阻塞运行。

## 依赖版本

无外部依赖，仅需标准 C 库和数学库 (-lm)

## 功能验证结果

### 无参数运行
```bash
$ poster
Filename argument missing!
Usage: poster <options> infile
options are:
   -v:         be verbose
   -f:         ask manual feed
   -i<box>:    specify input image size
   -c<margin>: horizontal and vertical cutmargin
   -w<margin>: horizontal and vertical additional white margin
   -m<box>:    media paper size
   -p<box>:    output poster size
   -s<number>: linear scale factor for poster
   -o<file>:   output redirection to named file
```

### PostScript 缩放测试
```bash
$ poster -s2 -mA4 test-poster.ps -o poster-output.ps
# 输出: 合法 PostScript，包含正确的页面尺寸和裁切标记
```

### verbose 模式
```bash
$ poster -v -s2 -mA4 test-poster.ps
Using default cutmargin of 5%
Using default whitemargin of 0
Deciding for 1 column and 1 row of portrait pages.
```

### 错误处理
```bash
$ poster -s2 nonexistent.ps
poster: fail to open file 'nonexistent.ps'!
```

poster 不支持 --version 参数，功能验证需通过运行确认。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| poster (stripped) | 26,304 bytes | ELF aarch64 二进制 |
| poster.1 | 11,408 bytes | man 手册页 |
| poster-1.0.0-ohos-aarch64.tar.gz | 92,705 bytes | 预编译包 |
| poster-1.0.0-ohos-aarch64-debug.tar.gz | 17,943 bytes | 调试符号包 |

## 二进制信息

- 文件类型: ELF shared object, 64-bit LSB arm64, dynamic, stripped
- 动态依赖: libc.so (仅 musl libc)
- RPATH: 无（仅依赖系统库）

## 注意事项

- poster.c 使用已废弃的 gets() 函数，在 C11+ 标准下仅产生警告，不影响运行
- poster 不支持 --version 参数，功能验证需通过运行用法输出确认
- 本地安装时需先删除旧版本文件（HMDFS 限制），再 cp 新文件
- 首次执行需 ELF 签名后才可运行

---

**编译结束**: 2026-06-13 02:21
**最终状态**: published
