# mokutil 0.7.2 — 编译适配笔记

## 基本信息

| 项目 | 值 |
|------|------|
| 软件名 | mokutil |
| 版本 | 0.7.2 |
| 构建系统 | autotools |
| 编译器 | clang |
| 目标平台 | OpenHarmony (aarch64, musl libc) |

## 依赖

| 依赖 | 版本 | 来源 |
|------|------|------|
| openssl | 3.5.6 | 预编译包 |
| efivar | 39 | 手动编译（共享库安装到 ~/usr/local） |
| libkeyutils | 1.6.3 | 手动编译（静态库安装到 ~/usr/local） |
| libcrypt | 系统自带 | musl libc |
| bash-completion | — | 未安装（可选依赖） |

## 配置选项

```bash
./configure --prefix=$DEFAULT_PREFIX --disable-strict
```

- `--disable-strict` 禁用 `-Werror` 和部分严格警告
- `PKG_CONFIG_PATH` 必须包含 efivar 和 libkeyutils 的 .pc 文件路径

## 编译问题及修复

### 问题 1: config.status Permission denied

**现象**: `config.status[752]: can't create ./confXXXX/subs1.awk: Permission denied`

**原因**: HMDFS 文件系统 setgid 目录 + umask 077 创建的临时目录 owner 为 20001006（非当前 uid 20020101），group 权限为空（--S），当前用户作为 group member 无法写入

**修复**: `sed -i 's/umask 077/umask 007/g' configure` — 将临时目录 umask 改为 007，确保 group 可读写

**知识类别**: 平台限制（L1）

### 问题 2: wchar_t typedef 冲突

**现象**: clang 报错 `typedef redefinition with different types ('unsigned short' vs 'unsigned int')`

**原因**: `-fshort-wchar` 使 clang 内建 wchar_t 为 unsigned short，但 musl libc `alltypes.h` 定义 wchar_t 为 unsigned int（aarch64）

**修复**: 移除 configure.ac 中的 `-fshort-wchar` 标志。mokutil 不直接使用 wchar_t，仅依赖 efi_char16_t（uint16_t）

**知识类别**: 平台限制（L1）

### 问题 3: musl 缺少 l64a() 和 getspnam()

**现象**: `mokutil.c:333: error: call to undeclared function 'l64a'` 和 `mokutil.c:438: error: call to undeclared function 'getspnam'`

**原因**: musl libc 不提供 glibc 扩展函数 l64a()（long 到 base64 字符串）和 getspnam()（shadow password 读取），也不提供 `<shadow.h>` 和 `struct spwd`

**修复**: 创建 musl_shim.c/h，提供兼容实现：
- `l64a()`: 使用 `./0-9A-Za-z` base64 字母表转换 32-bit 整数
- `getspnam()`: 始终返回 NULL（OpenHarmony 无 shadow password）
- `struct spwd`: 定义 shadow password 结构体（兼容声明）
- 在 mokutil.c 中 `#include <shadow.h>` → `#include "musl_shim.h"`

**知识类别**: 平台限制（L1）

### 问题 4: efivar 头文件安装

**现象**: `fatal error: 'fix_coverity.h' file not found`

**原因**: 安装了 efivar 的内部头文件 `src/efivar.h`（private header）而非公共头文件 `src/include/efivar/efivar.h`

**修复**: 从 `src/include/efivar/` 安装所有公共头文件（efivar.h, efivar-types.h, efivar-dp.h, efivar-time.h, efivar-guids.h, efiboot.h 等）

**知识类别**: 构建经验（L2）

## 补丁列表

| 补丁 | 描述 |
|------|------|
| 0001-configure.ac.patch | 移除 -fshort-wchar 标志 |
| 0002-src-Makefile.am.patch | 添加 musl_shim.c/h 到 SOURCES |
| 0003-src-mokutil.c.patch | 替换 #include <shadow.h> 为 #include "musl_shim.h" |
| 0004-src-musl_shim.c.patch | 新增：l64a() 和 getspnam() musl 兼容实现 |
| 0005-src-musl_shim.h.patch | 新增：兼容声明头文件 |

## 安装产物

| 文件 | 路径 |
|------|------|
| mokutil (binary) | `$PREFIX/bin/mokutil` |
| mokutil.1 (man page) | `$PREFIX/share/man/man1/mokutil.1` |

---

*编译结束*: 2026-06-09
*最终状态*: published
---

**编译结束**: 2026-06-09 10:24
**最终状态**: built
