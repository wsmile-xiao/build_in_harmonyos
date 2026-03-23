# 软件编译依赖关系与推荐顺序

> 本文档记录鸿蒙系统上常用软件的编译依赖关系和推荐编译顺序。
> 基于实际编译经验总结，遵循此顺序可避免因依赖缺失导致的重复编译。

---

## 推荐编译顺序

```
第一阶段：基础工具链（无外部依赖）
├── GNU sed 4.9           # 替代 toybox sed，很多 configure 脚本依赖
├── GNU coreutils 9.10    # 替代 toybox (包含 expr) ⚠️ 部分编译
└── GNU gawk 5.3.0        # 替代 toybox awk，很多构建脚本依赖

第二阶段：Autotools 工具链
├── automake 1.16.5       # 需要 autoconf, perl ⚠️ 有鸡生蛋问题
└── libtool 2.4.7         # 需要 automake, autoconf ⚠️ libtoolize 功能受限

第三阶段：基础库（按依赖顺序）
├── zlib 1.3.1            # 压缩库（无依赖）⭐ 优先编译
├── bzip2 1.0.8           # 压缩库（无依赖）
├── lzma 5.6.2            # 压缩库（无依赖）
├── openssl 1.1.1w        # SSL库（需要 perl）⭐ 依赖 zlib
├── ncurses 6.4           # 终端库（无依赖）⚠️ 必须使用 --without-shared
├── readline 8.2          # 命令行编辑（需要 ncurses）⭐ 依赖 ncurses
├── libffi 3.4.4/3.5.2    # 外部函数接口
├── gettext 0.22.5        # 国际化
└── gdbm 1.23             # 数据库（可选 readline）

第四阶段：网络工具
├── wget 1.19.1           # HTTP/HTTPS 下载（依赖 openssl）
├── rsync 3.3.0           # 文件同步
└── jq 1.7.1              # JSON 处理

第五阶段：系统工具
├── bash 5.3              # GNU Shell ⚠️ 必须使用 --without-bash-malloc
├── file 5.45             # 文件类型识别（建议 --enable-static）
├── htop 3.4.1            # 进程查看器（需要 sudo 运行）
├── strace 6.19           # 系统调用追踪 ⚠️ 必须使用 --disable-mpers
└── patch 2.7.6           # 补丁工具
                        ⚠️ strace ptrace 受 SELinux 限制，编译成功但无法实际追踪
                        参考: knowledge/ptrace-alternatives.md

第六阶段：编程语言（依赖前面所有阶段的库）
├── Python 3.9.0          # 依赖 zlib, openssl, ncurses, readline, gdbm, libffi
└── (其他语言)

第七阶段：文档系统
├── man-db 2.13.1         # 手册页系统 ⚠️ 需要 VPATH 构建 + automake 绕过
└── libpipeline 1.5.8     # man-db 的核心依赖（管道抽象库）
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
✅ 3. 编译 openssl（依赖 zlib，必须 no-asm）
✅ 4. 编译 ncurses（无依赖，必须 --without-shared）
✅ 5. 编译 readline（依赖 ncurses）
✅ 6. 编译 Python（依赖上述所有库）
```

---

## 依赖关系图

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
                           └─────────────────────────────────────┘
```

```
python ──┬── openssl ── zlib
         ├── libffi
         ├── ncurses ── (无依赖)
         └── readline ── ncurses

htop ──── ncurses
bash ──── readline ── ncurses
gdbm ──── (无外部依赖)
wget ──── openssl
rsync ──── (无外部依赖)
strace ─── (无外部依赖，⚠️ ptrace 受限)

automake ── autoconf (系统预装)
libtool ── autoconf, automake
coreutils ── (无外部依赖)
```

---

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
| ncurses | - | - | readline, bash, python, htop |
| readline | ncurses | - | bash, python, gdb |

### SSL/加密

| 软件 | 必需依赖 | 可选依赖 | 被依赖 |
|------|----------|----------|--------|
| openssl | perl | zlib | python, wget, curl, git |

### 数据库

| 软件 | 必需依赖 | 可选依赖 | 被依赖 |
|------|----------|----------|--------|
| gdbm | - | readline | python |

### 编程语言

| 软件 | 必需依赖 | 可选依赖 | 被依赖 |
|------|----------|----------|--------|
| Python | - | zlib, openssl, ncurses, readline, gdbm, libffi | 大量软件 |
| bash | - | ncurses, readline | 脚本 |

### 系统工具

| 软件 | 必需依赖 | 可选依赖 | 被依赖 |
|------|----------|----------|--------|
| strace | - | - | - |
| rsync | - | - | - |
| wget | openssl | - | - |
| htop | ncurses | - | - |
| file | - | - | - |

### 文档系统

| 软件 | 必需依赖 | 可选依赖 | 被依赖 | 编译注意 |
|------|----------|----------|--------|----------|
| libpipeline | - | libgio (GLib) | man-db | 标准 autotools，无特殊问题 |
| man-db | libpipeline, gdbm | bzip2, zlib | - | ⚠️ VPATH 构建 + automake 绕过 + 多个 HarmonyOS 补丁 |

---

## 关键编译选项速查

以下编译选项是鸿蒙环境特有的，**必须**使用：

| 软件 | 必须选项 | 原因 |
|------|----------|------|
| openssl | `no-asm` | 鸿蒙 clang 不支持此汇编格式 |
| ncurses | `--without-shared` | 共享库会覆盖系统版本导致 Shell 崩溃 |
| bash | `--without-bash-malloc` | 内置 malloc 与 musl 不兼容 |
| strace | `--disable-mpers` | 鸿蒙无 32 位兼容层 |
| file | `--enable-static` | SELinux 限制动态库加载 |

---

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

| 库 | Python 模块 | 缺失影响 | 安装必要性 |
|---|-------------|----------|-----------|
| zlib | _zlib, zipfile, gzip | 无法处理 zip/gzip 文件 | ⭐⭐⭐ 必须 |
| openssl | _ssl, _hashlib, urllib | 无法 HTTPS 连接 | ⭐⭐⭐ 必须 |
| ncurses | _curses | 无终端 UI | ⭐⭐ 推荐 |
| readline | readline | 无命令行编辑历史 | ⭐⭐ 推荐 |
| gdbm | _gdbm, dbm | 无数据库支持 | ⭐ 可选 |
| bzip2 | _bz2 | 无法处理 bz2 文件 | ⭐ 可选 |
| lzma | _lzma | 无法处理 xz 文件 | ⭐ 可选 |

---

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

*最后更新：2026-03-23（新增 man-db 2.13.1 / libpipeline 1.5.8 依赖链）*
SSL 正确链接。

---

*最后更新：2026-03-23*
