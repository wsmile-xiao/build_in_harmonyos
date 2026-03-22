# 软件依赖关系图

本文档记录鸿蒙系统上常用软件的编译依赖关系，帮助确定编译顺序。

## 推荐编译顺序

```
第一阶段：基础工具链
├── GNU sed 4.9           # 替代 toybox sed
├── GNU coreutils 9.10    # 替代 toybox (包含 expr)
└── GNU gawk 5.3.0        # 替代 toybox awk

第二阶段：Autotools 工具链
├── automake 1.16.5       # 需要 autoconf, perl
└── libtool 2.4.7         # 需要 automake, autoconf

第三阶段：基础库（按依赖顺序）
├── zlib 1.3.1            # 压缩库（无依赖）- ⭐ 优先编译
├── bzip2 1.0.8           # 压缩库（无依赖）
├── lzma 5.6.2            # 压缩库（无依赖）
├── openssl 1.1.1w        # SSL库（需要 perl）- ⭐ 依赖 zlib
├── ncurses 6.4           # 终端库（无依赖）- ⚠️ 使用 --without-shared
├── readline 8.2          # 命令行编辑（需要 ncurses）- ⭐ 依赖 ncurses
└── gdbm 1.23             # 数据库（可选 readline）

第四阶段：编程语言
├── Python 3.9.0          # 需要 zlib, openssl, ncurses, readline, gdbm
└── (其他语言)

第五阶段：应用软件
└── 按需编译
```

### ⚠️ 编译顺序的重要性

**关键原则**：
1. **工具链先行**：先编译 GNU 工具替代 toybox，避免工具兼容性问题
2. **依赖库按序编译**：zlib → openssl → ncurses → readline
3. **静态库优先**：对于系统关键依赖的库（如 ncurses），使用静态库避免冲突

**错误示例**：
```
❌ 先编译 Python，再编译 zlib
   → Python 缺少 _zlib 模块，需要重新编译

❌ 在工具链未就绪时编译 autotools 项目
   → toybox sed/expr 导致 configure 生成错误 Makefile
```

**正确示例**：
```
✅ 1. 编译 GNU coreutils（包含 expr）
✅ 2. 编译 zlib（无依赖）
✅ 3. 编译 openssl（依赖 zlib）
✅ 4. 编译 ncurses（无依赖，使用 --without-shared）
✅ 5. 编译 readline（依赖 ncurses）
✅ 6. 编译 Python（依赖上述所有库）
```

## 依赖关系图

```
                    ┌─────────────┐
                    │   sed 4.9   │
                    │ coreutils   │
                    │   gawk      │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  automake   │
                    │  libtool    │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐      ┌─────▼─────┐     ┌────▼────┐
    │  zlib   │      │  openssl  │     │ ncurses │
    │ bzip2   │      │           │     │         │
    │  lzma   │      └─────┬─────┘     └────┬────┘
    └─────────┘            │                │
         │                 │          ┌─────▼─────┐
         │                 │          │ readline  │
         │                 │          └─────┬─────┘
         │                 │                │
         └────────┬────────┴────────────────┘
                  │
           ┌──────▼──────┐
           │   Python    │
           │   3.9.0     │
           └─────────────┘
```

## 详细依赖表

### 基础工具

| 软件 | 必需依赖 | 可选依赖 | 被依赖 |
|------|----------|----------|--------|
| GNU sed | - | - | automake, libtool |
| GNU coreutils | - | gmp, libcap | automake, libtool |
| GNU gawk | - | mpfr, gmp | - |

### Autotools

| 软件 | 必需依赖 | 可选依赖 | 被依赖 |
|------|----------|----------|--------|
| automake | autoconf, perl | - | libtool |
| libtool | automake, autoconf | - | 多数 autotools 项目 |

### 压缩库

| 软件 | 必需依赖 | 可选依赖 | 被依赖 |
|------|----------|----------|--------|
| zlib | - | - | openssl, python, curl |
| bzip2 | - | - | python, tar |
| lzma | - | - | tar, dpkg |

### 终端库

| 软件 | 必需依赖 | 可选依赖 | 被依赖 |
|------|----------|----------|--------|
| ncurses | - | - | readline, bash, python |
| readline | ncurses | - | bash, python, gdb |

### SSL/加密

| 软件 | 必需依赖 | 可选依赖 | 被依赖 |
|------|----------|----------|--------|
| openssl | perl | zlib | python, curl, git |

### 数据库

| 软件 | 必需依赖 | 可选依赖 | 被依赖 |
|------|----------|----------|--------|
| gdbm | - | readline | python |

### 编程语言

| 软件 | 必需依赖 | 可选依赖 | 被依赖 |
|------|----------|----------|--------|
| Python | - | zlib, openssl, ncurses, readline, gdbm | 大量软件 |
| bash | - | ncurses, readline | 脚本 |

## 检查依赖是否安装

```bash
# 检查库文件
ls -la $HOME/usr/local/lib/libz.so
ls -la $HOME/usr/local/lib/libssl.so
ls -la $HOME/usr/local/lib/libncursesw.so
ls -la $HOME/usr/local/lib/libreadline.so
ls -la $HOME/usr/local/lib/libgdbm.so

# 检查头文件
ls -la $HOME/usr/local/include/zlib.h
ls -la $HOME/usr/local/include/openssl/ssl.h
ls -la $HOME/usr/local/include/ncurses.h
ls -la $HOME/usr/local/include/readline/readline.h

# 使用 pkg-config 检查
pkg-config --exists zlib && echo "zlib 已安装"
pkg-config --exists openssl && echo "openssl 已安装"
pkg-config --exists ncursesw && echo "ncurses 已安装"
pkg-config --exists readline && echo "readline 已安装"
```

## 常见依赖问题

### 问题1：找不到 -lz

```
configure: error: zlib library not found
```

**解决**：
```bash
export LIBRARY_PATH=$HOME/usr/local/lib:$LIBRARY_PATH
export C_INCLUDE_PATH=$HOME/usr/local/include:$C_INCLUDE_PATH
```

### 问题2：找不到 ncurses

```
configure: error: ncurses library not found
```

**解决**：
```bash
export CFLAGS="-I$HOME/usr/local/include/ncursesw $CFLAGS"
export LDFLAGS="-L$HOME/usr/local/lib -lncursesw $LDFLAGS"
```

### 问题3：Python 找不到模块

```
ModuleNotFoundError: No module named '_ssl'
```

**解决**：重新编译 Python，确保 OpenSSL 正确链接。

---

*文档版本: 1.1*  
*最后更新: 2024-03-22*

## 完整依赖关系图（ASCII艺术）

```
                           ┌─────────────────────────────────────┐
                           │         第一阶段：基础工具           │
                           │  sed, coreutils, gawk (无依赖)       │
                           └─────────────────┬───────────────────┘
                                             │
                           ┌─────────────────▼───────────────────┐
                           │         第二阶段：构建工具           │
                           │  automake, libtool (依赖基础工具)    │
                           └─────────────────┬───────────────────┘
                                             │
          ┌──────────────────┬───────────────┴───────────────┬──────────────────┐
          │                  │                               │                  │
┌─────────▼─────────┐ ┌──────▼──────┐              ┌─────────▼─────────┐ ┌───────▼───────┐
│    压缩库         │ │  SSL/加密   │              │    终端/UI        │ │    数据库     │
│  zlib, bzip2     │ │  openssl    │              │  ncurses          │ │  gdbm, sqlite │
│  lzma, xz        │ │  (需 perl)  │              │  (无依赖)         │ │               │
└─────────┬─────────┘ └──────┬──────┘              └─────────┬─────────┘ └───────┬───────┘
          │                  │                               │                  │
          │                  │                      ┌────────▼────────┐          │
          │                  │                      │    readline     │          │
          │                  │                      │  (需 ncurses)   │          │
          │                  │                      └────────┬────────┘          │
          │                  │                               │                  │
          └──────────────────┴───────────────┬───────────────┴──────────────────┘
                                             │
                           ┌─────────────────▼───────────────────┐
                           │         第三阶段：编程语言           │
                           │  Python, bash (依赖上述库)           │
                           └─────────────────┬───────────────────┘
                                             │
                           ┌─────────────────▼───────────────────┐
                           │         第四阶段：应用软件           │
                           │  git, curl, wget, vim 等            │
                           └─────────────────────────────────────┘
```

## Python 3.9 依赖详解

```
Python 3.9.0
    │
    ├── 必需依赖（无）
    │
    ├── 推荐依赖
    │   ├── zlib        → _zlib 模块（zip/gzip 支持）
    │   ├── openssl     → _ssl, _hashlib 模块（HTTPS 支持）
    │   ├── ncurses     → _curses 模块（终端 UI）
    │   ├── readline    → readline 模块（命令行编辑）
    │   ├── gdbm        → _gdbm 模块（数据库）
    │   ├── bzip2       → _bz2 模块（bz2 压缩）
    │   └── lzma        → _lzma 模块（xz 压缩）
    │
    └── 可选依赖
        ├── sqlite3     → _sqlite3 模块（需先编译 sqlite）
        ├── tk          → _tkinter 模块（GUI）
        └── gdb         → 调试支持
```

## 各库对 Python 模块的影响

| 库 | Python 模块 | 缺失影响 | 安装必要性 |
|---|-------------|----------|-----------|
| zlib | _zlib, zipfile, gzip | 无法处理 zip/gzip 文件 | ⭐⭐⭐ 必须 |
| openssl | _ssl, _hashlib, urllib | 无法 HTTPS 连接 | ⭐⭐⭐ 必须 |
| ncurses | _curses | 无终端 UI | ⭐⭐ 推荐 |
| readline | readline | 无命令行编辑历史 | ⭐⭐ 推荐 |
| gdbm | _gdbm, dbm | 无数据库支持 | ⭐ 可选 |
| bzip2 | _bz2 | 无法处理 bz2 文件 | ⭐ 可选 |
| lzma | _lzma | 无法处理 xz 文件 | ⭐ 可选 |

## 编译前依赖检查脚本

```bash
#!/bin/bash
# check_dependencies.sh - 检查编译依赖是否就绪

echo "=== 编译依赖检查 ==="
echo ""

check_tool() {
    if command -v "$1" &> /dev/null; then
        echo "✅ $1: $(which $1)"
        return 0
    else
        echo "❌ $1: 未安装"
        return 1
    fi
}

check_lib() {
    lib_file="$HOME/usr/local/lib/$1"
    if [ -f "$lib_file" ]; then
        echo "✅ $1: 存在"
        return 0
    else
        echo "❌ $1: 未找到 ($lib_file)"
        return 1
    fi
}

check_header() {
    header_file="$HOME/usr/local/include/$1"
    if [ -f "$header_file" ]; then
        echo "✅ $1: 存在"
        return 0
    else
        echo "⚠️  $1: 未找到 ($header_file)"
        return 1
    fi
}

echo "--- 编译工具 ---"
check_tool clang
check_tool make
check_tool autoconf
check_tool automake
check_tool perl
echo ""

echo "--- 基础库 ---"
check_lib libz.so
check_lib libz.a
check_lib libssl.so
check_lib libcrypto.so
check_lib libncursesw.so
check_lib libreadline.so
check_lib libgdbm.so
check_lib libbz2.so
check_lib liblzma.so
check_lib libffi.so
echo ""

echo "--- 头文件 ---"
check_header zlib.h
check_header openssl/ssl.h
check_header ncurses.h
check_header readline/readline.h
check_header gdbm.h
check_header bzlib.h
check_header lzma.h
check_header ffi.h
echo ""

echo "--- pkg-config ---"
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig"
pkg-config --exists zlib && echo "✅ zlib pkg-config" || echo "⚠️ zlib pkg-config 未配置"
pkg-config --exists openssl && echo "✅ openssl pkg-config" || echo "⚠️ openssl pkg-config 未配置"
pkg-config --exists ncursesw && echo "✅ ncurses pkg-config" || echo "⚠️ ncurses pkg-config 未配置"
echo ""

echo "=== 检查完成 ==="
```