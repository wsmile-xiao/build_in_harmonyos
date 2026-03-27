# Python 3.9.0 HarmonyOS 适配指南

> **版本**: 5.1 | **更新日期**: 2026-03-27 | **状态**: ✅ 完全可用

## 概述

| 项目 | 信息 |
|------|------|
| 软件版本 | Python 3.9.0 |
| 目标平台 | HarmonyOS aarch64 (musl libc, clang 15.0.4) |
| 补丁数量 | 24 个（0001-0024） |
| C 扩展模块 | 204 个 .so 文件 |
| 核心模块 | 18/18 全部通过 |
| 设计原则 | 最小侵入 — 只添加 HarmonyOS 条件分支，不修改上游逻辑 |

## 快速开始

```bash
# 1. 环境准备（~/.zshrc 中应有以下配置）
export TMPDIR=$HOME/tmp
export CC=clang CXX=clang++ AR=llvm-ar RANLIB=llvm-ranlib
export CFLAGS="-fPIC -O2" LDFLAGS="-L$HOME/usr/local/lib"
export CPPFLAGS="-I$HOME/usr/local/include"

# 2. 下载源码
curl -L -o Python-3.9.0.tgz https://www.python.org/ftp/python/3.9.0/Python-3.9.0.tgz
tar -xzf Python-3.9.0.tgz && cd Python-3.9.0

# 3. 应用补丁
PATCHDIR=/storage/Users/currentUser/renshang/build_in_harmonyos/archives/p/python/3.9.0/patches
for p in $(grep -v '^#\|^$' "$PATCHDIR/series"); do
    patch -p1 < "$PATCHDIR/$p"
done

# 4. 构建并安装
autoconf
./configure --prefix=$HOME/usr/local \
  --disable-ipv6 \
  ac_cv_file__dev_ptmx=no \
  ac_cv_file__dev_ptc=no \
  --enable-shared \
  --enable-optimizations
make -j$(nproc)
make install

# 5. 验证
LD_LIBRARY_PATH=$HOME/usr/local/lib python3.9 -c "
import sys; print('Python:', sys.version)
print('Platform:', sys.platform)
for m in ['math','ssl','ctypes','hashlib','sqlite3','tempfile',
          'ensurepip','subprocess','multiprocessing','venv','_locale']:
    __import__(m); print(f'  ✅ {m}')
"
```

---

## 一、环境要求

### 1.1 ~/.zshrc 关键配置

以下环境变量影响 Python 编译，**必须正确设置**：

```bash
# === 编译工具链 ===
export CC="clang"
export CXX="clang++"
export AR="llvm-ar"
export RANLIB="llvm-ranlib"
export NM="llvm-nm"
export STRIP="llvm-strip"
export OBJDUMP="llvm-objdump"
export OBJCOPY="llvm-objcopy"
export AS="llvm-as"
export LD="ld.lld"

# === 编译选项 ===
export CFLAGS="-fPIC -O2"
export CXXFLAGS="-fPIC -O2"
export LDFLAGS="-L$HOME/usr/local/lib"
export CPPFLAGS="-I$HOME/usr/local/include"

# === 运行时 ===
export TMPDIR=$HOME/tmp           # /tmp 只读
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH

# === 包管理 ===
export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
export DEFAULT_PREFIX=$HOME/usr/local
```

### 1.2 ⚠️ 不要设置的变量

```bash
# ❌ 不要设置 C_INCLUDE_PATH / CPLUS_INCLUDE_PATH
#    原因：会与 pkg-config --cflags 冲突，导致返回空值
#    正确做法：用 CPPFLAGS="-I$HOME/usr/local/include"

# ❌ 不要设置 LIBRARY_PATH
#    原因：会与构建系统冲突
#    正确做法：用 LDFLAGS="-L$HOME/usr/local/lib"
```

### 1.3 前置依赖

| 依赖 | 用途 | 安装位置 | 必需？ |
|------|------|----------|--------|
| gettext 0.22.5 | CJK 编解码模块 | `$HOME/usr/local` | ⚠️ 推荐 |
| OpenSSL 1.1.1w | _ssl 模块 | `$HOME/usr/local` | ⚠️ 推荐 |
| ncurses 6.4 | curses 模块 | `$HOME/usr/local` | ⚠️ 可选 |
| readline 8.2 | 交互式输入 | `$HOME/usr/local` | ⚠️ 可选 |
| gdbm 1.23 | dbm/gdbm 模块 | `$HOME/usr/local` | ⚠️ 可选 |
| zlib 1.3.1 | zlib 模块 | `$HOME/usr/local` | ⚠️ 推荐 |
| bzip2 1.0.8 | bz2 模块 | `$HOME/usr/local` | ⚠️ 推荐 |
| libffi 3.4.4 | ctypes 模块 | `$HOME/usr/local` | ⚠️ 推荐 |
| SQLite3 | sqlite3 模块 | 系统自带 | ✅ 已有 |

### 1.4 gettext 特别说明

HarmonyOS SDK 自带一个**空壳** `libintl.h`（只定义了 `__USE_GNU_GETTEXT` 宏，没有 `textdomain()` 等函数声明）。如果 `CPPFLAGS` 未包含 `-I$HOME/usr/local/include`，configure 会找到 SDK 的空壳头文件，导致 `_localemodule.c` 编译失败（`-Werror=implicit-function-declaration`）。

**解决方案**：安装完整 gettext 0.22.5 到 `$HOME/usr/local`，并确保 `CPPFLAGS="-I$HOME/usr/local/include"` 在 configure 时生效。

---

## 二、补丁清单

### 2.1 设计原则

> **最小侵入**：只添加 HarmonyOS 条件分支（`if sys.platform.startswith(('ohos', 'harmonyos'))` 或 `#ifdef __OHOS__`），**不修改上游已有逻辑**，**不修复上游 bug**。

| 原则 | 说明 |
|------|------|
| 只添加，不修改 | 在上游 if/else 中插入 HarmonyOS elif 分支 |
| 不修复上游 bug | 即使 `pid == -1` 是死代码也不在适配补丁中修复 |
| 不假设上游遗漏 | 不把 `sys.platform == 'win32'` 改为 `hasattr(os, 'fork')` |
| 新文件不受限 | `_harmonyos_compat.py` 等新文件可自由设计 |

### 2.2 完整补丁列表（24 个）

```
# CPython 3.9.0 HarmonyOS Patch Set v2
# Principle: minimal invasion — only add HarmonyOS-specific branches
#
# --- 核心构建系统 (0001-0007) ---
0001-configure-ac-harmonyos-support.patch        # configure.ac 平台检测（10 处修改）
0002-config.guess-harmonyos-support.patch         # config.guess 三元组识别
0003-config.sub-harmonyos-support.patch           # config.sub OS 验证
0004-Makefile.pre.in-harmonyos-fixes.patch        # BUILDPYTHON/HARDLINK/LDSHARED
0005-setup.py-harmonyos-support.patch             # SDK 路径 + 扩展模块编译
0006-distutils-util-get-platform.patch            # get_platform() → "ohos-*"
0007-sysconfig-harmonyos-platform.patch           # sysconfig 平台字符串

# --- 子进程兼容层 (0008-0011) ---
0008-harmonyos-compat-new-file.patch              # _harmonyos_compat.py 新文件（仅 os.system）
0009-site.py-auto-import-compat.patch              # site.py 自动导入兼容层
0010-bootsubprocess-pipe-workaround.patch          # _bootsubprocess.py SELinux 绕过
0011-subprocess-lazy-import-fallback.patch         # subprocess 延迟导入 + fork_exec fallback

# --- 运行时修复 (0012-0024) ---
0012-pythread-h-native-thread-id.patch            # pythread.h 声明
0013-thread-pthread-h-native-thread-id.patch      # thread_pthread.h 实现
0014-multiprocessing-spawn-default-ohos.patch      # multiprocessing 默认 spawn
0015-multiprocessing-util-abstract-sockets.patch   # abstract sockets
0016-posixsubprocess-fd-dir.patch                 # _posixsubprocess.c FD_DIR /dev/fd
0017-posixmodule-sendfile.patch                   # posixmodule.c sendfile NULL offset
0018-timemodule-musl-timezone.patch               # timemodule.c musl 时区
0019-ctypes-util-skip-ldconfig.patch              # ctypes/util.py 跳过 ldconfig
0020-posixpath-defpath.patch                      # posixpath.py defpath 平台守卫
0021-venv-symlink-fallback.patch                  # venv symlink → makedirs 降级
0022-pylifecycle-fd-validation.patch              # pylifecycle.c dup() fd 验证
0023-tempfile-uuid-ohos-paths.patch               # tempfile.py + uuid.py 鸿蒙路径
0024-shutil-sendfile-ohos.patch                   # shutil sendfile 平台扩展
```

### 2.3 补丁格式规范

| 项目 | 规范 |
|------|------|
| 文件名 | `{NNNN}-{模块}-{描述}.patch`（描述性命名） |
| 路径前缀 | 统一 `a/` `b/` 格式（`patch -p1`） |
| 依赖顺序 | 按 series 文件顺序应用，0001→0024 |
| 应用验证 | `for p in $(grep -v '^#\|^$' series); do patch -p1 < $p; done` |

---

## 三、构建系统适配详解

### 3.1 三层构建模型

```
┌─────────────────────────────────────────────────┐
│  第一层：平台检测（config.guess / config.sub）    │
│  → 识别 HarmonyOS，生成 aarch64-linux-ohos 三元组  │
├─────────────────────────────────────────────────┤
│  第二层：配置生成（configure.ac → configure）      │
│  → 设置 MACHDEP、LDSHARED、BLDSHARED 等变量     │
├─────────────────────────────────────────────────┤
│  第三层：构建执行（Makefile / setup.py）           │
│  → 编译链接、扩展模块构建、安装                    │
└─────────────────────────────────────────────────┘
```

### 3.2 核心适配点

#### 3.2.1 musl BIND_NOW 问题

musl libc 默认启用 `BIND_NOW`，要求动态链接时所有符号必须立即解析。Python 扩展模块（`.so`）如果不链接 `libpython`，导入时会报 `symbol not found`。

**解决方案**（补丁 0001 + 0004）：

| 变量 | 值 | 说明 |
|------|-----|------|
| `LDSHARED` | `$(CC) -shared -L. -lpython$(LDVERSION)` | 扩展模块链接时包含 `-lpython` |
| `BLDSHARED` | `$(CC) -shared` | 构建 `libpython.so` 本身（不能链接自己） |
| `LINKFORSHARED` | `-Xlinker -export-dynamic` | 导出符号供扩展模块使用 |

**验证**：`llvm-readelf -d _struct.so | grep NEEDED`，应包含 `libpython3.9.so`。

#### 3.2.2 HMDFS 大小写不敏感

HMDFS 文件系统不区分大小写，`python` 和 `Python` 是同一个名字。Makefile 中 `BUILDPYTHON=python$(BUILDEXE)` 的链接目标与源码目录 `Python/` 冲突。

**解决方案**（补丁 0004）：

```diff
- BUILDPYTHON = python$(BUILDEXE)
+ BUILDPYTHON = python$(VERSION)$(BUILDEXE)
```

产物变为 `python3.9`，不再冲突。

#### 3.2.3 SELinux 域转换限制

`os.execv()` 执行 SDK 工具时，SELinux 域转换导致权限丢失。但 `os.system("cmd | cat")` 通过管道创建子进程，绕过域转换限制。

**解决方案**（补丁 0010 + 0008）：
- `_bootsubprocess.py`：setup.py 编译扩展模块时用管道语法绕过
- `_harmonyos_compat.py`：运行时只对 `os.system` 加管道包装（`subprocess.Popen` **不 patch**，因为补丁 0011 已让 posix_spawn 在鸿蒙上正常工作）

> **⚠️ 重要**：`_harmonyos_compat.py` v5.0 曾经对 `subprocess.Popen` 做了全局 monkey-patch（强制 `shell=True` + `cmd 2>&1 | cat`），这会导致所有需要 stdin 交互的子进程操作永久阻塞（如 `python -i`、`os.read(stdin)` 等）。v5.1 已移除该 patch，只保留 `os.system` 的包装。

#### 3.2.4 HMDFS 不支持 symlink

用户目录（HMDFS）上 `os.symlink()` 100% 失败（`PermissionError`）。

**解决方案**（补丁 0021）：
```python
try:
    os.symlink('lib', 'lib64')
except OSError:
    os.makedirs('lib64', exist_ok=True)  # HarmonyOS fallback
```

#### 3.2.5 硬链接不可用

SELinux 策略禁止硬链接。

**解决方案**（补丁 0004）：
```makefile
HARDLINK = cp -p   # 替代 ln
LN_FORCE = rm -f && ln -s  # 替代 ln -sf（toybox bug）
```

---

## 四、已知构建注意事项

以下是历次构建中遇到的卡点及解决方案：

### 4.1 gettext 头文件冲突

| 项目 | 说明 |
|------|------|
| 症状 | `_localemodule.c` 编译失败：`textdomain` 隐式函数声明 |
| 根因 | SDK 空壳 `libintl.h` 被找到，而非 `$HOME/usr/local/include/libintl.h` |
| 解决 | 确保 `CPPFLAGS="-I$HOME/usr/local/include"` |

### 4.2 HMDFS 大小写冲突

| 项目 | 说明 |
|------|------|
| 症状 | `ld.lld: error: cannot open output file python: Is a directory` |
| 根因 | `BUILDPYTHON=python` 与源码 `Python/` 目录同名 |
| 解决 | 补丁 0004 改为 `BUILDPYTHON=python$(VERSION)` |

### 4.3 autoconf 版本

| 项目 | 说明 |
|------|------|
| 症状 | autoconf 2.72 生成的 configure 可能产生不同的检测结果 |
| 建议 | 如遇问题，尝试用 `autoconf` 重生成 `configure` |

### 4.4 /tmp 只读

| 项目 | 说明 |
|------|------|
| 症状 | configure 和 Python 运行时需要写临时文件 |
| 解决 | `export TMPDIR=$HOME/tmp && mkdir -p $TMPDIR` |

### 4.5 ELF 签名

| 项目 | 说明 |
|------|------|
| 症状 | 修改 ELF 后执行报 `Operation not permitted` |
| 根因 | HarmonyOS 的 adhoc 签名机制 |
| 解决 | DevBox 弹窗授权，或重新编译 |

---

## 五、验证结果（2026-03-27）

### 5.1 构建验证

| 项目 | 结果 |
|------|------|
| 补丁应用 | 24/24 全部成功（`patch -p1`，零 fuzz） |
| autoconf | ✅ 成功 |
| configure | ✅ 成功 |
| make -j | ✅ 零错误 |
| make install | ✅ 完整成功 |
| ensurepip | ✅ pip 自动安装 |

### 5.2 运行时验证

| 项目 | 结果 |
|------|------|
| Python 版本 | 3.9.0 |
| sys.platform | `ohos` |
| C 扩展 .so | 204 个 |
| 核心模块 | 18/18 ✅ |

**核心模块清单**：

| 模块 | 状态 | 说明 |
|------|:----:|------|
| math | ✅ | 数学运算 |
| ssl | ✅ | HTTPS（依赖 OpenSSL） |
| ctypes | ✅ | FFI（依赖 libffi） |
| hashlib | ✅ | 哈希（依赖 OpenSSL） |
| sqlite3 | ✅ | SQLite |
| tempfile | ✅ | 临时文件 |
| ensurepip | ✅ | pip 安装器 |
| subprocess | ✅ | 子进程 |
| multiprocessing | ✅ | 多进程（spawn 模式） |
| venv | ✅ | 虚拟环境 |
| _locale | ✅ | 国际化（依赖 gettext） |
| _posixsubprocess | ✅ | POSIX 子进程 C 扩展 |
| _harmonyos_compat | ✅ | 鸿蒙兼容层 |
| datetime | ✅ | 日期时间 |
| json | ✅ | JSON |
| zlib | ✅ | zlib 压缩 |
| lzma | ✅ | LZMA 压缩 |
| bz2 | ✅ | bzip2 压缩 |

---

## 六、补丁规范化历程

### v1 → v2 变更（2026-03-27）

原始补丁（24 个，0001-0024）存在风格混杂、注释为中文、部分修改了上游逻辑等问题。重构后：

| 项目 | v1 | v2 |
|------|----|----|
| 补丁数量 | 24（0001-0024） | 24（0001-0024，内容重组） |
| 文件命名 | 4 种 diff 路径前缀混用 | 统一 `a/` `b/` 前缀 + 描述性名称 |
| 代码注释 | 中文 | 英文 |
| 上游侵入 | 部分补丁修改了上游逻辑 | 最小侵入，只添加 HarmonyOS 分支 |
| UPSTREAM 候选 | 3 个（改上游逻辑） | 0 个（所有修改均为 downstream） |

### 核心修复

1. **`_bootsubprocess.py wait()`**：恢复原始 fork/exec 路径，仅对 HarmonyOS 添加 `os.system()` 分支
2. **`subprocess _use_posix_spawn()`**：恢复原始 `pass`，仅对 HarmonyOS 返回 True
3. **`multiprocessing get_all_start_methods()`**：恢复原始 if/else 结构，插入 HarmonyOS elif
4. **`Makefile BUILDPYTHON`**：改为 `python$(VERSION)` 解决 HMDFS 大小写冲突
5. **清理 `_OHOS_PIPE_WORKAROUND`**：删除约 50 行死代码（临时文件方案已废弃）

---

## 七、相关文件

| 文件 | 用途 |
|------|------|
| `patches/` | 24 个适配补丁 + series |
| `patches/series` | 补丁应用顺序 |
| `scripts/package_python.sh` | 打包脚本 |
| `tests/test_subprocess_compat.py` | 子进程兼容性测试 |
| `manifest.yaml` | 元数据 |

---

## 八、依赖关系

### 编译依赖链

```
gettext 0.22.5  → CJK 编解码模块
OpenSSL 1.1.1w → ssl, hashlib 模块
ncurses 6.4    → curses 模块
readline 8.2   → readline 模块
zlib 1.3.1     → zlib 模块
bzip2 1.0.8    → bz2 模块
libffi 3.4.4   → ctypes 模块
gdbm 1.23      → dbm/gdbm 模块
    ↓
Python 3.9.0   → 最终目标
    ↓
pip / setuptools / wheel / 虚拟环境
```

### 下游依赖

pip、setuptools、wheel、NumPy、Requests、Django/Flask 等所有 Python 软件包。

---

## 九、版本历史

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-03-21 | 1.0 | 初始适配 |
| 2026-03-21 | 2.0 | 补丁详解完善 |
| 2026-03-21 | 3.0 | 添加依赖关系 |
| 2026-03-25 | 3.1 | 新增 venv symlink fallback |
| 2026-03-25 | 4.0 | 全量构建验证，64 扩展模块 |
| 2026-03-26 | 4.2 | --enable-shared 修复，libpython 导出 1459 符号，72/72 导入 |
| 2026-03-27 | **5.0** | **补丁规范化重构**：24 补丁最小侵入、英文注释、HMDFS 修复、gettext 支持、204 扩展模块、make install 完整成功 |
| 2026-03-27 | 5.1 | 精简 _harmonyos_compat.py（移除 subprocess.Popen/os.popen monkey-patch，修复测试卡死）；修复 configure.ac 末尾残留 |

---

*维护者: OpenHarmony 社区*
