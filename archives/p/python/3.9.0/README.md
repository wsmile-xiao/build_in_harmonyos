# Python 3.9.0 HarmonyOS 适配指南（Final Release）

> **版本**: 6.0 (Final) | **日期**: 2026-03-30 | **状态**: ✅ Release

## 概述

| 项目 | 信息 |
|------|------|
| 软件版本 | Python 3.9.0 |
| 目标平台 | HarmonyOS aarch64 (musl libc, clang 15.0.4) |
| 补丁数量 | 78 个（27 核心 + 51 测试） |
| 官方测试 | 425/425 完成，383 通过（90.1%） |
| C 扩展模块 | 204 个 .so 文件 |
| 核心模块 | 18/18 全部通过 |
| ctypes | ✅ 0 ERROR（需 libffi ≥ 3.5.2） |
| 设计原则 | 最小侵入 — 只添加 `#ifdef __OHOS__` / `sys.platform == 'ohos'` 分支 |

## 快速开始

```bash
# 1. 环境变量（必须）
export TMPDIR=$HOME/tmp
export CC=clang CXX=clang++ AR=llvm-ar RANLIB=llvm-ranlib
export CFLAGS="-fPIC -O2" LDFLAGS="-L$HOME/usr/local/lib"
export CPPFLAGS="-I$HOME/usr/local/include"
export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig

# 2. 下载源码
curl -L -o Python-3.9.0.tgz https://www.python.org/ftp/python/3.9.0/Python-3.9.0.tgz
tar -xzf Python-3.9.0.tgz && cd Python-3.9.0

# 3. 应用补丁（78 个，按 series 顺序）
PATCHDIR=/path/to/build_in_harmonyos/archives/p/python/3.9.0/patches
for p in $(grep -v '^#\|^$' "$PATCHDIR/series"); do
    patch -p1 < "$PATCHDIR/$p"
done

# 4. 构建
autoconf   # configure.ac 已修改，需重新生成 configure
./configure --prefix=$HOME/usr/local \
  --disable-ipv6 \
  ac_cv_file__dev_ptmx=no \
  ac_cv_file__dev_ptc=no \
  --enable-shared
make -j$(nproc)
make install

# 5. 验证
LD_LIBRARY_PATH=$HOME/usr/local/lib python3.9 -c "
import sys; print('Python:', sys.version, '| Platform:', sys.platform)
for m in ['math','ssl','ctypes','hashlib','sqlite3','tempfile',
          'ensurepip','subprocess','multiprocessing','venv','_locale']:
    __import__(m); print(f'  ✅ {m}')
"
```

---

## 一、环境要求

### 1.1 必须设置的环境变量

```bash
CC="clang" CXX="clang++" AR="llvm-ar" RANLIB="llvm-ranlib"
NM="llvm-nm" STRIP="llvm-strip" OBJCOPY="llvm-objcopy"
CFLAGS="-fPIC -O2" CXXFLAGS="-fPIC -O2"
LDFLAGS="-L$HOME/usr/local/lib"
CPPFLAGS="-I$HOME/usr/local/include"
TMPDIR=$HOME/tmp                        # /tmp 只读
PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig
```

### 1.2 不要设置

```
C_INCLUDE_PATH / CPLUS_INCLUDE_PATH  → 会与 pkg-config --cflags 冲突
LIBRARY_PATH                          → 会与构建系统冲突
```

### 1.3 前置依赖

| 依赖 | 版本 | 用途 | 必需 |
|------|------|------|------|
| gettext | 0.22.5 | _locale 模块（SDK 有空壳 libintl.h，**必须**装完整版） | ⚠️ 强烈推荐 |
| OpenSSL | 1.1.1w | ssl, hashlib | 推荐 |
| zlib | 1.3.1 | zlib 模块 | 推荐 |
| bzip2 | 1.0.8 | bz2 模块 | 推荐 |
| libffi | ≥ 3.5.2 | ctypes 模块（3.5.2 修复了 W^X closure 分配） | 推荐 |
| ncurses | 6.4 | curses 模块 | 可选 |
| readline | 8.2 | 交互式输入 | 可选 |
| gdbm | 1.23 | dbm/gdbm 模块 | 可选 |
| SQLite3 | 系统自带 | sqlite3 模块 | ✅ |

### 1.4 gettext 特别说明

SDK 自带空壳 `libintl.h`（仅 `#define __USE_GNU_GETTEXT`，无函数声明）。
若 `CPPFLAGS` 缺少 `-I$HOME/usr/local/include`，configure 找到空壳头文件，
`_localemodule.c` 编译报 `implicit-function-declaration`。

---

## 二、补丁清单

### 2.1 设计原则

| 原则 | 说明 |
|------|------|
| 最小侵入 | 只添加 `__OHOS__` / `sys.platform == 'ohos'` 条件分支 |
| 不改上游逻辑 | 不修复上游 bug，不修改已有 if/else 分支 |
| 新文件自由设计 | `_harmonyos_compat.py` 等新文件不受限 |
| 测试补丁独立 | 跳过平台限制测试，不影响运行时 |

### 2.2 补丁分类

完整列表见 `patches/series`。按功能分为 9 组，共 78 个补丁：

| 组 | 分类 | 补丁数 | 说明 |
|----|------|:------:|------|
| 1 | 构建系统 | 5 | configure.ac, config.guess/sub, Makefile.pre.in, setup.py |
| 2 | 线程 | 2 | pythread.h, thread_pthread.h (native thread ID) |
| 3 | 进程生命周期 | 1 | pylifecycle.c (fd 验证) |
| 4 | 子进程兼容层 | 4 | _harmonyos_compat.py, _bootsubprocess.py, subprocess.py, _posixsubprocess.c |
| 5 | 多进程 | 2 | multiprocessing context.py, util.py |
| 6 | POSIX/Time/CTypes | 4 | posixmodule.c, timemodule.c, _ctypes_callbacks.c, ctypes_util.py |
| 7 | 路径/兼容/工具 | 9 | posixpath, sysconfig, distutils, site, shutil, compileall, tempfile, uuid, venv |
| 8 | 测试基础设施 | 6 | test warnings/bdb/importlib filters |
| 9 | 测试跳过 | 45 | 平台限制测试 skip/filter |

**核心补丁（组 1-7）：27 个** — 编译和运行所必需
**测试补丁（组 8-9）：51 个** — 仅运行 regrtest 时需要

### 2.3 核心适配点

#### musl BIND_NOW（组 1, configure.ac + Makefile.pre.in）

musl 默认 `BIND_NOW`，扩展模块必须链接 `libpython`：
- `LDSHARED = $(CC) -shared -L. -lpython$(LDVERSION)` （扩展模块）
- `BLDSHARED = $(CC) -shared` （libpython 本身，不能链接自己）

#### HMDFS 大小写不敏感（组 1, Makefile.pre.in）

`BUILDPYTHON=python` 与源码 `Python/` 冲突 → 改为 `python$(VERSION)`

#### HMDFS 不支持 symlink（组 7, venv/__init__.py）

`os.symlink()` 100% 失败 → `makedirs()` 降级

#### 硬链接不可用（组 1, Makefile.pre.in）

`HARDLINK = cp -p`，`LN_FORCE = rm -f && ln -s`（toybox `ln -sf` 有 bug）

#### HMDFS 符号链接不可跟踪（组 1, Makefile.pre.in sharedinstall）

`make install` 创建的 `libpython3.9.so → libpython3.9.so.1.0` 无效
→ 用 `$(HARDLINK)` 替代 `$(LN_FORCE)` 复制

#### SELinux 域转换（组 4, subprocess + _bootsubprocess）

`fork() + execve()` 执行 SDK 工具被拦截 → `_use_posix_spawn()` 返回 True
→ `posix_spawn()` 路径不受限制，pip install / clang 编译正常

#### posix_spawn 稳定路径（组 4, subprocess.py）

musl 的 `posix_spawn()` 实现质量良好 → 替代 fork+exec 作为默认子进程路径

---

## 三、configure 参数

```bash
./configure --prefix=$HOME/usr/local \
  --disable-ipv6 \              # HarmonyOS 无 IPv6
  ac_cv_file__dev_ptmx=no \     # /dev/ptmx 被 Hmmac MAC 策略阻止
  ac_cv_file__dev_ptc=no \      # 无 /dev/ptc
  --enable-shared               # 生成 libpython3.9.so（扩展模块需要）
```

> 不使用 `--enable-optimizations`（PGO）— 需要 instrumented build + rerun，在鸿蒙上收益不大且耗时翻倍。

---

## 四、构建注意事项

| 问题 | 症状 | 解决 |
|------|------|------|
| gettext 空壳 | `_localemodule.c` 编译失败 | `CPPFLAGS="-I$HOME/usr/local/include"` |
| HMDFS 大小写 | `ld.lld: python: Is a directory` | 补丁自动处理 `BUILDPYTHON` |
| /tmp 只读 | configure/Python 写临时文件失败 | `export TMPDIR=$HOME/tmp` |
| ELF 签名 | 修改后 `Operation not permitted` | 重新签名（见 knowledge/packaging.md） |
| autoconf 版本 | configure 检测结果不一致 | 修改 configure.ac 后 `autoconf` 重新生成 |
| libffi ctypes | `test_ctypes` 63 ERROR | 升级 libffi 到 3.5.2（closure W^X 修复） |

---

## 五、测试结果（V6 Final, 2026-03-30）

| 指标 | 数值 |
|------|------|
| 总测试 | 425 |
| 通过 | **383 (90.1%)** |
| 失败 | 6 |
| 跳过 | 34 |
| 环境变更 | 2 |
| 完成率 | 100%（全部跑完） |
| 耗时 | 3 分 55 秒 |

### 失败测试（6个）

| 测试 | 根因 |
|------|------|
| test_generators | 生成器相关行为差异，需进一步分析 |
| test_pdb | 调试器测试，可能涉及终端交互 |
| test_regrtest | 测试框架自测（interrupted 子测试） |
| test_sundry | 杂项测试（distutils 相关） |
| test_threading | 线程测试，可能涉及 signal/fork 交互 |
| test_urllib2 | urllib2 测试，可能涉及网络/权限 |

### 跳过测试分类（34个）

| 类别 | 测试数 | 说明 |
|------|:------:|------|
| GUI (Tcl/Tk) | 6 | test_tcl, test_tix, test_tk, test_ttk_guionly, test_ttk_textonly, test_turtle |
| PTY/终端 | 4 | test_ioctl, test_openpty, test_pty, test_getpass |
| 多进程 (fork) | 3 | test_multiprocessing_fork/forkserver/spawn |
| 信号 | 1 | test_signal |
| 网络 | 3 | test_smtpnet, test_urllib2net |
| Locale/时区 | 3 | test_c_locale_coercion, test_locale, test_format |
| Windows | 4 | test_winconsoleio, test_winreg, test_winsound, test_msilib |
| 其他平台限制 | 10 | test_devpoll, test_gdb, test_idle, test_kqueue, test_distutils, test_embed, test_dbm_dumb, test_startfile, test_nis, test_ossaudiodev, test_spwd, test_zipfile64, test_uu |

详见 `reports/REGRTEST_V52_ANALYSIS.md` 和 `reports/COMPATIBILITY_ASSESSMENT.md`。

---

## 六、相关文件

| 文件 | 用途 |
|------|------|
| `patches/` | 78 个适配补丁 |
| `patches/series` | 补丁应用顺序（分 9 组） |
| `scripts/package_python.sh` | 可移植包打包脚本 |
| `manifest.yaml` | 完整元数据 |
| `reports/COMPATIBILITY_ASSESSMENT.md` | 最终兼容性评估报告 |
| `reports/ROADMAP.md` | 鸿蒙 Python 生态下一步规划 |
| `reports/REGRTEST_V52_ANALYSIS.md` | v52 测试详细分析 |
---

*Python 3.9.0 HarmonyOS 适配 — OpenHarmony PC Developer 社区*
