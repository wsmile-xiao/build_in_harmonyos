# ncurses 鸿蒙系统编译指南

本文档保留 ncurses 6.4 的历史适配记录，并在末尾记录当前 ncurses 6.6
静态宽字符配方的契约和验证边界。

## 版本索引

- ncurses 6.4：历史手工编译、风险和下游集成记录
- ncurses 6.6：当前 Conan 配方、完整上游入口和目标机验证合同

## 概述

本文档记录了 ncurses 6.4 在鸿蒙系统上的编译适配过程，包括遇到的问题、解决方案和注意事项。

---

## ⚠️ 重要风险提示

### 共享库风险

**在鸿蒙系统上编译 ncurses 共享库存在严重风险！**

| 风险 | 说明 | 后果 |
|------|------|------|
| **系统 Shell 崩溃** | 鸿蒙的 zsh 依赖 `libncursesw.so.6` | 符号链接问题导致所有终端无法使用 |
| **库冲突** | 用户编译的共享库可能与系统库冲突 | 系统不稳定或崩溃 |
| **恢复困难** | Shell 崩溃后无法执行命令 | 需要新终端或重启恢复 |

### 推荐方案：编译静态库

**强烈建议在鸿蒙系统上只编译静态库**，避免共享库问题：

```bash
./configure --prefix=$HOME/usr/local \
    --without-shared \        # 关键：不生成共享库
    --enable-widec \
    --enable-overwrite
```

### 如果必须使用共享库

1. 确保符号链接正确：
   ```bash
   cd $HOME/usr/local/lib
   ln -sf libncursesw.so.6.4 libncursesw.so.6
   ```

2. 测试前先验证 shell 正常：
   ```bash
   # 在新终端测试
   echo "Shell 正常"
   ```

3. 如遇崩溃，立即在新终端恢复：
   ```bash
   cd /storage/Users/currentUser/usr/local/lib
   ln -s libncursesw.so.6.4 libncursesw.so.6
   ```

---

## 软件信息

- **软件名称**: ncurses
- **版本**: 6.4
- **构建系统**: Autotools (configure)
- **下载地址**: https://ftp.gnu.org/gnu/ncurses/ncurses-6.4.tar.gz

## 鸿蒙环境

- **系统**: HarmonyOS
- **内核**: HongMeng Kernel
- **架构**: aarch64
- **编译器**: Clang 15.0.4
- **工具链**: LLVM (llvm-ar, llvm-ranlib, llvm-nm, llvm-strip)

## 编译步骤

### 1. 解压源码

```bash
tar -xzf ncurses-6.4.tar.gz
cd ncurses-6.4
```

### 2. 应用补丁

```bash
patch -p1 < 0001-port-for-ohos.patch
```

### 3. 配置

#### 方案 A：编译静态库（推荐）

**这是鸿蒙系统上的推荐方式**，不会影响系统稳定性：

```bash
export TMPDIR=$HOME/tmp
export PATH="$HOME/usr/local/bin:$PATH"  # 确保使用 GNU 工具

./configure --prefix=$HOME/usr/local \
    --without-shared \       # ⭐ 关键：不生成共享库
    --without-cxx \          # 不编译 C++ 绑定（可选）
    --without-cxx-binding \
    --enable-widec \         # 启用宽字符支持
    --enable-overwrite \     # 头文件安装到顶层
    --without-debug \
    --without-profile \
    --without-ada \
    --without-manpages \
    --without-progs \
    --without-tests
```

**生成的文件**：
```
$HOME/usr/local/lib/
├── libncursesw.a    # 主库（静态）
├── libpanelw.a      # 面板库（静态）
├── libmenuw.a       # 菜单库（静态）
└── libformw.a       # 表单库（静态）
```

#### 方案 B：编译共享库（有风险）

**⚠️ 警告：此方案可能导致系统 Shell 崩溃！**

```bash
export TMPDIR=$HOME/tmp
export PATH="$HOME/usr/local/bin:$PATH"

./configure --prefix=$HOME/usr/local \
    --with-shared \          # 生成共享库
    --enable-widec \
    --enable-overwrite
```

**风险说明**：
- 鸿蒙系统的 `/bin/zsh` 依赖 `libncursesw.so.6`
- 如果共享库符号链接不完整，会导致 zsh 无法启动
- **所有终端将无法使用**，需要在新终端中恢复

**如果选择共享库，必须确保符号链接正确**：
```bash
cd $HOME/usr/local/lib
# 检查符号链接
ls -la libncursesw.so*
# 如果缺少 libncursesw.so.6，创建它
ln -sf libncursesw.so.6.4 libncursesw.so.6
```

**⚠️ 重要：`--enable-overwrite` 选项**

默认情况下，ncurses 会将头文件安装到 `include/ncursesw/` 子目录：

```
$prefix/include/
├── ncursesw/
│   ├── curses.h      ← 头文件实际位置
│   ├── ncurses.h
│   └── ...
└── (无 curses.h)
```

但大多数软件（如 Python、readline）使用 `#include <curses.h>`，期望在 `include/` 目录下找到头文件。

**两种解决方案：**

| 方案 | 命令 | 说明 |
|------|------|------|
| `--enable-overwrite` | 编译时添加此选项 | 头文件直接安装到 `include/`（推荐） |
| 手动软链接 | 编译后执行 | 灵活，适用于已安装的情况 |

**如果不使用 `--enable-overwrite`，需要手动创建软链接：**

```bash
cd $HOME/usr/local/include
ln -sf ncursesw/curses.h curses.h
ln -sf ncursesw/ncurses.h ncurses.h
ln -sf ncursesw/term.h term.h
ln -sf ncursesw/termcap.h termcap.h
ln -sf ncursesw/unctrl.h unctrl.h
```

### 4. 编译

```bash
make
```

### 5. 安装

```bash
make install
```

## 补丁说明

### 修改文件

1. **config.guess**: 添加 HarmonyOS 系统检测
2. **config.sub**: 添加 `linux-ohos` 三元组支持

### 关键修改详解

#### 1. config.guess - HarmonyOS 系统识别

**问题背景**: GNU config 的 config.guess 不识别 HarmonyOS 系统，导致 configure 无法正确识别目标平台。

**技术原理**:
```
uname -s 在不同系统上的输出:
- Linux: "Linux"
- HarmonyOS: "HarmonyOS"
```

**解决方案**: 在 Linux 检测之前添加 HarmonyOS 检测：

```bash
*:HarmonyOS:*:*)
    case "$UNAME_MACHINE" in
        aarch64|arm64)
            MACHINE=aarch64
            ;;
        armv7*|armv8*)
            MACHINE=arm
            ;;
        x86_64|amd64)
            MACHINE=x86_64
            ;;
        i?86)
            MACHINE=i686
            ;;
        *)
            MACHINE="$UNAME_MACHINE"
            ;;
    esac
    GUESS=${MACHINE}-unknown-linux-ohos
    ;;
```

**修改位置**: 在 `*:Linux:*:*)` 检测之前

**目标三元组说明**:
- 格式: `cpu-vendor-kernel-os`
- HarmonyOS: `aarch64-unknown-linux-ohos`
- `linux-ohos` 表示使用 Linux 内核 API 但运行在 HarmonyOS 上

#### 2. config.sub - 操作系统验证

**问题背景**: config.sub 用于验证目标三元组的合法性，需要添加 `ohos` 作为有效的操作系统标识。

**修改内容**:

1. 在有效操作系统列表中添加 `ohos*`：
```bash
# 原始
-linux* | -kfreebsd* | ...
# 修改后
-linux* | -ohos* | -kfreebsd* | ...
```

2. 在内核-操作系统验证中添加 `linux-ohos*`：
```bash
-linux-gnu* | -linux-musl* | ...
# 添加
-linux-ohos*
```

**技术说明**: 
- `ohos` 作为操作系统后缀，与 `gnu`、`musl` 并列
- 表示使用 HarmonyOS 的用户空间和 API

## 遇到的问题

### 问题 1: toybox expr 复合正则表达式 Bug（根本原因）

**现象**: 
- config.status 执行时，子目录 Makefile 中的 `top_srcdir` 被错误设置为乱码
- 乱码模式有规律，像是内存数据被错误输出

**排查过程**:
```bash
# 追踪 config.status 执行
bash -x ./config.status --file=ncurses/Makefile 2>&1 | grep ac_dir

# 发现变量值异常
+ ac_dots='../<乱码>...'
```

**根本原因**:
- 鸿蒙默认使用 **toybox expr**
- toybox expr 在处理**复合正则表达式**（使用 `\|` 操作符）时存在严重 bug
- autoconf 的 config.status 使用复杂的 expr 命令来提取路径组件

**问题复现**:
```bash
# toybox expr (错误)
$ expr X"ncurses/Makefile" : 'X\(.*[^/]\)//*[^/][^/]*/*$' \| . : '\(.\)'
mOkk...  # 输出乱码

# GNU expr (正确)
$ expr X"ncurses/Makefile" : 'X\(.*[^/]\)//*[^/][^/]*/*$' \| . : '\(.\)'
ncurses  # 正确输出
```

**技术分析**:
```
config.status 中的 expr 命令链:
expr X"$ac_file" : 'X\(.*[^/]\)//*[^/][^/]*/*$' \
  \| X"$ac_file" : 'X\(//\)[^/]' \
  \| X"$ac_file" : 'X\(//\)$' \
  \| X"$ac_file" : 'X\(/\)' \
  \| . : '\(.\)'

这个命令链用于从路径中提取目录部分：
- 输入: "ncurses/Makefile"
- 预期输出: "ncurses"
- toybox 输出: 乱码（复合正则表达式处理 bug）
```

**解决方案**: 
- 编译安装 **GNU coreutils**（包含正确的 GNU expr）
- 设置 PATH 优先使用 GNU 工具

```bash
# 编译 GNU coreutils
cd /path/to/coreutils-9.10
./configure --prefix=$HOME/usr/local --disable-nls
make
cp src/expr $HOME/usr/local/bin/

# 设置 PATH
export PATH="$HOME/usr/local/bin:$PATH"
```

### 问题 2: 临时目录不可写

**现象**: configure 过程中无法创建临时文件

**解决方案**: 设置 `TMPDIR` 环境变量

```bash
export TMPDIR=$HOME/tmp
mkdir -p $TMPDIR
```

## 经验总结

### HarmonyOS 工具链差异

| 方面 | Linux | HarmonyOS |
|------|-------|-----------|
| expr | GNU expr | toybox expr (复合正则有 bug) |
| sed | GNU sed | toybox sed / GNU sed |
| awk | gawk/mawk | toybox awk |
| shell | bash | mksh/sh |
| 临时目录 | /tmp 可写 | 需要设置 TMPDIR |

### 关键发现

1. **toybox expr 的 bug 是隐蔽的**:
   - 简单的正则表达式工作正常
   - 复合正则表达式（`\|` 操作符）输出乱码
   - 这导致 autotools 项目生成的 Makefile 出现问题

2. **需要安装的关键 GNU 工具**:
   - **GNU coreutils** (expr 是最关键的)
   - **GNU sed** (用于复杂脚本)

3. **PATH 优先级非常重要**:
   ```bash
   export PATH="$HOME/usr/local/bin:$PATH"
   ```

### 注意事项

1. **先安装 GNU coreutils**: 在编译其他 autotools 项目前，先安装 GNU coreutils

2. **环境变量设置**:
   ```bash
   export TMPDIR=$HOME/tmp
   export PATH="$HOME/usr/local/bin:$PATH"
   ```

3. **编译顺序建议**:
   - GNU coreutils (提供 expr)
   - GNU sed
   - 其他 autotools 项目 (如 ncurses)

## 相关项目

- **GNU coreutils**: 提供 GNU expr，解决 toybox expr bug
- **GNU sed**: 替代 toybox sed，完整支持复杂脚本

## 编译产物

编译成功后生成以下库文件：

- libncursesw.so.6.4 - 主库（宽字符版本）
- libformw.so.6.4 - 表单库
- libmenuw.so.6.4 - 菜单库
- libpanelw.so.6.4 - 面板库
- libncurses++w.a - C++ 绑定（静态库）

## 参考资料

- ncurses 官方文档: https://invisible-island.net/ncurses/
- GNU config: https://git.savannah.gnu.org/cgit/config.git/
- GNU coreutils 鸿蒙适配: build_in_harmonyos/c/coreutils/9.9/README.md
- 鸿蒙编译知识库: build_in_harmonyos/SKILL.md

## 版本历史

- 2026-03-21: 添加 ln -s 权限问题解决方案，修复头文件安装问题
- 2026-03-21: 添加静态库编译方案和风险提示，添加 Python curses 模块静态链接说明
- 2026-03-15: 更新问题分析，明确 toybox expr bug 为根本原因
- 2026-03-14: 初始版本，完成 ncurses 6.4 鸿蒙适配

---

## 鸿蒙系统特有问题及解决方案

### 问题 3: ln -s 创建软链接权限被拒绝

**现象**:
```bash
$ ln -s ncursesw/curses.h curses.h
ln: cannot create symbolic link 'curses.h' to 'ncursesw/curses.h': Permission denied
```

**根本原因**:
- 鸿蒙系统的 SELinux/MAC 安全策略限制了用户进程创建软链接的权限
- 这是**鸿蒙系统的通用限制**，不是 ncurses 特有的问题

**详细分析**: 参见 `build_in_harmonyos/SKILL.md` 第 3.7.3 节"SELinux 策略对软链接的限制"

**解决方案**: 使用 `cp` 复制代替 `ln -s` 软链接

```bash
# 不要使用软链接
# ln -s ncursesw/curses.h curses.h  # ❌ 会失败

# 使用复制代替
cp ncursesw/curses.h curses.h  # ✅ 正常工作
cp ncursesw/ncurses.h ncurses.h
cp ncursesw/term.h term.h
cp ncursesw/termcap.h termcap.h
cp ncursesw/unctrl.h unctrl.h
cp ncursesw/panel.h panel.h
cp ncursesw/form.h form.h
cp ncursesw/menu.h menu.h
cp ncursesw/eti.h eti.h
cp ncursesw/ncurses_dll.h ncurses_dll.h
```

**推荐方法**: 使用 `--enable-overwrite` 选项，让 configure 自动处理

```bash
./configure --prefix=$HOME/usr/local \
    --without-shared \
    --enable-widec \
    --enable-overwrite    # ⭐ 头文件直接安装到 include/
```

**注意事项**:
- 复制的文件是独立的，不会随源文件更新
- 如果重新安装 ncurses，需要重新复制头文件
- `--enable-overwrite` 选项会自动处理这个问题（推荐）

### 问题 4: 头文件 include 路径不正确

**现象**:
编译 Python 时报错：
```
fatal error: curses.h: No such file or directory
```

或者：
```
error: 'cchar_t' undeclared
```

**原因分析**:

1. **头文件位置问题**:
   - 如果不使用 `--enable-overwrite`，头文件安装在 `include/ncursesw/` 子目录
   - Python 的 `#include <curses.h>` 找不到文件

2. **头文件内容问题**:
   - `include/ncursesw/curses.h` 中的 include 路径是 `#include <ncursesw/xxx.h>`
   - 而顶层 `include/curses.h` 应该是 `#include <xxx.h>`

**解决方案**:

**方案 A: 使用 `--enable-overwrite` 选项（推荐）**

```bash
./configure --prefix=$HOME/usr/local \
    --without-shared \
    --enable-widec \
    --enable-overwrite    # ⭐ 头文件自动安装到顶层
```

**方案 B: 手动复制头文件**

如果不使用 `--enable-overwrite`，需要手动处理：

```bash
cd $HOME/usr/local/include

# 方法1: 复制文件（推荐，因为 ln -s 会失败）
cp ncursesw/curses.h curses.h
cp ncursesw/ncurses.h ncurses.h
# ... 其他头文件

# 方法2: 修复 include 路径（需要修改文件内容）
# 将 curses.h 中的 #include <ncursesw/xxx.h> 改为 #include <xxx.h>
sed -i 's|#include <ncursesw/|#include <|g' curses.h
```

**验证头文件正确性**:
```bash
# 检查 include 路径
grep -n "#include" $HOME/usr/local/include/curses.h | head -10

# 应该看到类似：
# 89:#include <ncurses_dll.h>
# 而不是：
# 89:#include <ncursesw/ncurses_dll.h>
```

### 完整的清理和重新安装流程

如果之前安装有问题，可以按以下步骤清理重装：

```bash
# 1. 清理旧的库文件
cd $HOME/usr/local/lib
rm -f libncurses* libcurses* libpanel* libmenu* libform* libtic* libtinfo*
rm -f *.so*  # 清理共享库残留

# 2. 清理旧的头文件
cd $HOME/usr/local/include
rm -f curses.h ncurses.h ncurses_dll.h term.h termcap.h unctrl.h eti.h form.h menu.h panel.h
rm -rf ncursesw

# 3. 重新编译安装（使用正确的选项）
cd /path/to/ncurses-6.4
make distclean  # 清理编译产物

./configure --prefix=$HOME/usr/local \
    --without-shared \
    --enable-widec \
    --enable-overwrite \
    --without-debug \
    --without-profile \
    --without-ada \
    --without-manpages \
    --without-progs \
    --without-tests \
    --without-cxx \
    --without-cxx-binding

make -j$(nproc)
make install

# 4. 验证安装
ls -la $HOME/usr/local/lib/libncursesw.a
ls -la $HOME/usr/local/include/curses.h
grep -n "#include" $HOME/usr/local/include/curses.h | head -5
```

---

## 附录：Python curses 模块编译指南

### 问题：宽字符函数未定义

Python 编译 `_curses` 模块时可能报错：
```
error: unknown type name 'cchar_t'; did you mean 'wchar_t'?
error: call to undeclared function 'setcchar'
error: call to undeclared function 'wadd_wch'
```

### 原因分析

ncurses 的宽字符函数（`cchar_t`、`setcchar`、`wadd_wch` 等）是**条件编译**的：

```c
#if defined(_XOPEN_SOURCE_EXTENDED) || (defined(_XOPEN_SOURCE) && (_XOPEN_SOURCE - 0 >= 500))
#define NCURSES_WIDECHAR 1
```

| 平台 | C库 | `_XOPEN_SOURCE` 状态 | 需要添加宏？ |
|------|-----|---------------------|--------------|
| Linux | glibc | 默认定义且 >= 500 | ❌ 不需要 |
| macOS | - | 默认不定义 | ✅ 需要 |
| HarmonyOS | musl | 未定义 | ✅ 需要 |

### 解决方案

**方案 A：修改 Python setup.py（推荐）**

Python 补丁 `0009-setup.py-curses-XOPEN_SOURCE_EXTENDED.patch` 已修改 `setup.py`：

```python
if MACOS or OHOS:
    curses_defines.append(('_XOPEN_SOURCE_EXTENDED', '1'))
```

**方案 B：手动编译时添加宏**

```bash
clang -c -fPIC \
    -DHAVE_NCURSESW=1 \
    -D_XOPEN_SOURCE_EXTENDED \   # ⭐ 关键：启用宽字符函数
    -D_XOPEN_SOURCE=600 \
    -I$HOME/usr/local/include \
    -I./Include -I. \
    Modules/_cursesmodule.c \
    -o _cursesmodule.o
```

### 编译命令

```bash
# 编译 _curses 模块
clang -c -fPIC \
    -DHAVE_NCURSESW=1 \
    -D_XOPEN_SOURCE_EXTENDED \
    -D_XOPEN_SOURCE=600 \
    -I$HOME/usr/local/include \
    -I./Include -I. \
    Modules/_cursesmodule.c \
    -o _cursesmodule.o

# 静态链接
clang -shared -L. -lpython3.9 \
    _cursesmodule.o \
    $HOME/usr/local/lib/libncursesw.a \
    -o _curses.so

# 编译 _curses_panel 模块
clang -c -fPIC \
    -DHAVE_NCURSESW=1 \
    -D_XOPEN_SOURCE_EXTENDED \
    -I$HOME/usr/local/include \
    -I./Include -I. \
    Modules/_curses_panel.c \
    -o _curses_panel.o

# 静态链接
clang -shared -L. -lpython3.9 \
    _curses_panel.o \
    $HOME/usr/local/lib/libpanelw.a \
    $HOME/usr/local/lib/libncursesw.a \
    -o _curses_panel.so
```

### 关键点说明

| 要点 | 说明 |
|------|------|
| `-D_XOPEN_SOURCE_EXTENDED` | 必须添加，否则 `cchar_t`、`setcchar` 等宽字符类型和函数未定义 |
| 静态链接顺序 | `libpanelw.a` 必须在 `libncursesw.a` 之前 |
| 无运行时依赖 | 静态链接后，不依赖系统 ncurses 共享库 |

### 详细文档

Python 编译完整指南：`build_in_harmonyos/p/python/3.9.0/README.md`

---

## ncurses 6.6

ncurses 6.6 is packaged as static wide-character libraries to avoid shadowing the
platform `libncursesw.so.6`. The package includes all five library components, public
headers, command-line tools, and the complete terminfo database.

### Adaptation notes

- Preserve all 86 upstream `test/programs` entrypoints and run the complete
  `make -j1 check` target.
- Patch upstream `config.guess` so native platform detection yields
  `aarch64-unknown-linux-ohos`; do not force build, host, or target triplets.
- Reject the platform `expr` implementation when it cannot evaluate Autoconf compound
  expressions, allowing the GNU implementation from the build environment to be used.
- Run generated header installation helpers through the configured shell on HMDFS.
- Cache `setfsuid` as unavailable after the target probe is confirmed to trigger
  syscall 151/SIGSYS. No source or patch uses an OHOS conditional macro.

### Conan contract

The `ncurses/6.6` recipe exports the `ncurses::ncurses` CMake target and `ncursesw`
pkg-config identity. It supplies consumer-first static link order, packaged terminfo
environment variables, and tool paths. Consumer tests cover CMake `FindCurses`, wide
character output, `tputs`, terminfo lookup, windows, panels, menus, and forms.

The package has no third-party Conan prerequisite. Its HarmonyOS build environment
requires Bash, GNU Make, Clang, Gawk, GNU sed, and a compatible GNU `expr`.
