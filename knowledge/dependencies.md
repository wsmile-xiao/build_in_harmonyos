# 软件编译依赖关系与推荐顺序

> 本文档记录鸿蒙系统上常用软件的编译依赖关系和推荐编译顺序。
> 基于实际编译经验总结，遵循此顺序可避免因依赖缺失导致的重复编译。

---

## 推荐编译顺序

> ⚠️ **pkg-config 优先**：pkg-config 是编译生态的基石，几乎所有 C/C++ 构建系统都依赖它来发现已安装的库。
> 如果系统预装的 pkg-config 不可用或有问题，应**最先编译安装 pkg-config**，甚至早于 sed/coreutils/gawk。
> 详见 `environment.md` §11.7。鸿蒙系统预装了 pkg-config 0.29.2，一般情况下可直接使用。

```
第零阶段：pkg-config（如系统预装版本不可用时）
└── pkg-config              # ⭐ 编译生态基石，后续几乎所有软件的 configure 都依赖它
                            # 编译方式: ./configure --prefix=$DEFAULT_PREFIX --with-internal-glib

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

**解决**：确保 `PKG_CONFIG_PATH` 包含 zlib 的 .pc 文件所在目录：
```bash
export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
```

> ⚠️ **不要设置 `C_INCLUDE_PATH`**：该变量会与 pkg-config 冲突，导致 `--cflags` 返回空。详见 `environment.md` §11。

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

### 问题4：测试框架依赖 Perl，需要单独编译（跨软件知识）

**问题描述**：许多 GNU 软件的测试套件使用 Perl 编写，需要额外的 CPAN 模块。
如果 Perl 环境未正确配置，测试无法运行，导致无法验证编译产物的正确性。

**根因分析**：

| 缺失类型 | 具体表现 | 影响软件 |
|----------|----------|----------|
| **CPAN 模块缺失** | `Can't locate HTTP/Daemon.pm` | wget、curl |
| **Perl 版本不兼容** | 系统预装的 Perl 版本过旧 | 需要新 Perl 特性的软件 |
| **Perl 未安装** | `perl: command not found` | OpenSSL Configure 等 |

**解决方案**：

```bash
# 安装 cpanm
curl -L https://cpanmin.us -o cpanm
chmod +x cpanm

# 安装常用测试模块
./cpanm --notest HTTP::Daemon HTTP::Message LWP Test::More

# 配置本地 Perl 库
mkdir -p ~/perl-lib
export PERL5LIB="$HOME/perl-lib/lib/perl5:$PERL5LIB"
export PERL_MM_OPT="INSTALL_BASE=$HOME/perl-lib"
export PERL_MB_OPT="--install_base $HOME/perl-lib"
```

**跨软件影响**：

Perl 不仅是测试框架依赖，它也是构建链中的关键依赖（automake、libtool、OpenSSL Configure 都用 Perl 编写）。
建议将 Perl 放在编译顺序的第二阶段，确保其 CPAN 模块环境配置正确。

**相关文件**：`harmonyos-specifics.md §14`（Perl 测试框架依赖问题详细分析）

> 来源：`archives/p/python/3.9.0/manifest.yaml`

---

## 静态编译强制要求表

> **🔴 核心安全规则**：某些库如果以共享库形式安装到用户目录，会通过 `LD_LIBRARY_PATH` 覆盖系统版本，
> 导致系统工具（Shell、终端等）崩溃。这些库**必须静态编译**。

### 危险等级分类

| 等级 | 库名 | 强制选项 | 根因 | 后果 |
|------|------|---------|------|------|
| 🔴 **必须静态** | ncurses | `--without-shared` | libncursesw.so 覆盖系统版本 → **Shell 崩溃，终端不可用** | 系统级故障 |
| 🟠 **强烈建议** | readline | `--disable-shared` | libreadline.so 版本冲突 → bash/zsh 异常 | Shell 功能异常 |
| 🟠 **建议静态** | zlib | `--static` 或只装 .a | libz.so 被预编译包加载 → 链接错误 | 编译/运行时失败 |
| 🟢 可选动态 | openssl, bzip2, lzma | 默认即可 | 冲突风险较低 | 通常无问题 |

### 判断标准：一个库是否需要静态编译？

回答以下问题，任一为"是"则应考虑静态编译：

```
Q1: 系统是否有同名的预装共享库？
    → 是：存在覆盖风险
    → 否：安全

Q2: 系统的关键进程（Shell、终端、窗口管理器）是否依赖该库？
    → 是：🔴 必须静态（如 ncurses）
    → 否：看 Q3

Q3: 该库是否会被 LD_LIBRARY_PATH 意外加载？
    → 是：用户设置 LD_LIBRARY_PATH 后所有子进程受影响
    → 否：相对安全

Q4: 该库的 SONAME 是否与系统版本不同？
    → 不同：即使被加载也不会实际覆盖（较安全）
    → 相同：⚠️ 高风险
```

### LD_LIBRARY_PATH 陷阱详解

#### 问题机制

```
用户编译 ncurses 为共享库 → 安装到 $HOME/usr/local/lib/libncursesw.so.6.4
    ↓
用户或预编译包 activate.sh 设置：
    export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
    ↓
用户打开新终端（zsh/bash）
    ↓
终端进程继承 LD_LIBRARY_PATH
    ↓
动态链接器搜索 libncursesw.so.6 时：
    1. 先找 $HOME/usr/local/lib/libncursesw.so.6.4 ← 找到了！
    2. 不再搜索系统路径 /usr/lib/libncursesw.so.6
    ↓
但用户版本的 libncursesw.so 缺少某些符号或 ABI 不兼容
    ↓
终端调用 ncurses 函数 → crash / hang / 显示异常
    ↓
结果：所有终端不可用，用户无法操作电脑
```

#### 为什么不能简单地"不设置 LD_LIBRARY_PATH"？

预编译包的可移植性依赖于 RPATH + LD_LIBRARY_PATH：

```
方案 A：只用 RPATH（$ORIGIN 相对路径）
    ✅ 优点：不影响系统库
    ❌ 缺点：只能找到包内库，无法利用系统已装的库

方案 B：RPATH + LD_LIBRARY_PATH
    ✅ 优点：灵活，可覆盖/补充系统库
    ⚠️ 缺点：LD_LIBRARY_PATH 全局生效，可能污染系统

方案 C：RPATH + activate.sh 精确控制（推荐）
    ✅ 只在需要时 source activate.sh
    ✅ deactivate 时恢复原环境
    ⚠️ 但如果用户在激活状态下启动终端，仍会污染
```

#### 最佳实践

```bash
# 对于危险库（ncurses 等），坚决静态编译
./configure --without-shared --prefix=$PREFIX   # ncurses
./configure --disable-shared --prefix=$PREFIX    # readline

# 预编译包的 activate.sh 中不要包含危险库路径
# 即使用户的 lib/ 下有 libncursesw.a，也不会通过 LD_LIBRARY_PATH 加载
```

---

## 内嵌依赖处理策略

> 当软件内嵌了其他项目的源码作为依赖（如 pkg-config 内嵌 glib、Python 内嵌 sqlite/expat），
> 这些内嵌依赖的处理方式与独立编译的依赖不同。

### 分类与策略

| 类型 | 示例 | 处理方式 | 归档归属 |
|------|------|---------|---------|
| **可选内嵌** | pkg-config `--with-internal-glib` | 使用内嵌版本，补丁放在主软件归档下 | 主软件 archives/p/pkg-config/ |
| **强制内嵌** | Python 内嵌 expat/sqlite3 | 无法禁用，补丁放在主软件归档下 | 主软件 archives/p/python/ |
| **可解耦** | 某些软件允许 `--with-external-xxx` | 优先使用外部独立编译的版本 | 各自独立归档 |

### 内嵌依赖补丁规范

```bash
# 补丁文件放在主软件归档下，路径反映内嵌关系
archives/p/pkg-config/0.29.2/patches/
├── 0001-ohos-fix-glib-config-guess.patch      # 修改内嵌 glib 的 config.guess
├── 0002-ohos-fix-glib-stdio-compat.patch       # 修改内嵌 glib 的源码
└── 0003-ohos-pkg-config-main-fix.patch         # 修改主软件自身代码

# manifest.yaml 中记录内嵌依赖信息
embedded_dependencies:
  - name: glib
    version: "2.38.2"
    reason: "--with-internal-glib (pkg-config 无法使用系统 glib)"
    patches_applied:
      - "0001-ohos-fix-glib-config-guess.patch"
      - "0002-ohos-fix-glib-stdio-compat.patch"
```

### 关键注意事项

1. **内嵌依赖的 config.guess/sub 通常非常旧**（2012-2014 年），几乎必定需要打补丁或用 `--build/--host` 覆盖
2. **内嵌依赖不应有独立的归档目录**——它是主软件的一部分
3. **如果内嵌依赖可以解耦为外部依赖，优先解耦**（便于复用和单独更新）

### 典型场景：pkg-config 内嵌 glib 2.38.2

这是目前遇到的最复杂的内嵌依赖案例，值得详细记录：

```
pkg-config 0.29.2
└── glib 2.38.2 (内嵌, --with-internal-glib)
    ├── configure.ac / configure    ← 需要打 OHOS 平台补丁
    ├── config.guess (2014 年版)     ← 缺少 HarmonyOS 检测
    ├── config.sub (2014 年版)      ← 缺少 ohos-linux 支持
    ├── Makefile (生成的)            ← -Werror 导致编译失败
    └── glib/ 目录下的源码           ← 可能需要兼容性补丁
```

**补丁分布示例**：

```
archives/p/pkg-config/0.29.2/patches/
├── 0001-ohos-update-config-sub-for-ohos.patch      # 主包的 config.sub
├── 0002-ohos-update-config-guess-for-harmonyos.patch # 主包的 config.guess
├── 0003-ohos-fix-configure-conftest-exec-pipe.patch  # 主包的 configure
├── 0004-ohos-fix-glib-configure-conftest.patch       # ⚬ 内嵌 glib 的 configure
├── 0005-ohos-fix-glib-Makefile-Werror.patch          # ⚬ 内嵌 glib 的 Makefile
└── scripts/
    └── post-configure-hook.sh                         # Makefile sed 自动化
```

**glib 特殊处理要点**：
- glib 2.38.2 太老，无法可靠地 `autoreconf` → 补丁只能打在② configure / ③ Makefile 层级
- `--with-internal-glib` 是唯一可行选项（系统无可用 glib）
- glib 的 `make clean` 会重新生成 Makefile → 需要 post-configure hook 脚本
- 如果未来 pkg-config 更新到使用更新的 glib 版本，应评估是否可以解耦为外部依赖

---

*最后更新：2026-04-04*
*新增 §静态编译强制要求表：危险等级分类 + 判断标准 + LD_LIBRARY_PATH 陷阱*
*新增 §内嵌依赖处理策略：分类/补丁规范/注意事项*
