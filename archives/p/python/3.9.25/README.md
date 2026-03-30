# Python 3.9.25 HarmonyOS 适配指南（Release）

> **版本**: 1.0 (Release) | **日期**: 2026-03-30 | **状态**: ✅ Release
>
> Python 3.9 系列最终版本。基于 3.9.0 补丁集升级，经三目录 diff 法重新生成全部 104 个补丁。

## 概述

| 项目 | 信息 |
|------|------|
| 软件版本 | Python 3.9.25（3.9 系列最终版本） |
| 目标平台 | HarmonyOS aarch64 (musl libc, clang 15.0.4) |
| 补丁数量 | 104 个（13 核心 + 16 运行时 + 24 测试数据 + 51 测试适配） |
| 官方测试 | 425 完成，384 通过 / 8 失败 / 33 跳过（**90.4%**） |
| C 扩展模块 | 72 个 .so 文件 |
| 核心模块 | python3.9 + libpython3.9.so |
| ctypes | ✅ 0 ERROR（需 libffi ≥ 3.5.2） |
| 补丁生成 | 三目录 diff 法（`diff -ruN a/ b/`） |
| 补丁应用 | `patch -p1`（逐个应用，非 quilt） |
| 设计原则 | 最小侵入 — 只添加 `#ifdef __OHOS__` / `sys.platform == 'ohos'` 分支 |

---

## 快速开始

```bash
# 1. 环境变量（必须）
export TMPDIR=$HOME/tmp
export CC=clang CXX=clang++ AR=llvm-ar RANLIB=llvm-ranlib
export CFLAGS="-fPIC -O2" LDFLAGS="-L$HOME/usr/local/lib"
export CPPFLAGS="-I$HOME/usr/local/include"
export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig

# 2. 下载源码
curl -L -o Python-3.9.25.tgz https://www.python.org/ftp/python/3.9.25/Python-3.9.25.tgz
tar -xzf Python-3.9.25.tgz && cd Python-3.9.25

# 3. 应用补丁（104 个，按 series 顺序，patch -p1）
PATCHDIR=/path/to/build_in_harmonyos/archives/p/python/3.9.25/patches
for p in $(grep -v '^#\|^$' "$PATCHDIR/../series"); do
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

## 二、补丁说明

### 2.1 补丁生成方法：三目录 diff 法

本版本使用**三目录 diff 法**生成全部补丁，确保每个补丁都可独立 `patch -p1` 应用：

```
dir_a  = Python-3.9.25-clean      （原始 tgz 解压，未经任何修改）
dir_b  = Python-3.9.25-full-patch （手动修改 + 编译验证通过）
dir_c  = archives/p/python/3.9.25/patches（diff -ruN 生成）
```

生成命令：
```bash
diff -ruN dir_a/Include/pythread.h dir_b/Include/pythread.h > 0001-Include-pythread.h.patch
diff -ruN dir_a/Lib/subprocess.py   dir_b/Lib/subprocess.py   > 0013-Lib-subprocess.py.patch
# ... 104 个文件逐一 diff
```

验证：全部 104 个补丁在全新解压的 clean 目录上 `patch -p1` 应用成功。

> **与 quilt 的区别**：3.9.0 使用 quilt 管理补丁（series + .pc），3.9.25 改为直接
> `patch -p1`，因为补丁格式为标准 `diff -ruN a/ b/`，无需 quilt 元数据。
> `series` 文件仅记录应用顺序。

### 2.2 设计原则

| 原则 | 说明 |
|------|------|
| 最小侵入 | 只添加 `__OHOS__` / `sys.platform == 'ohos'` 条件分支 |
| 不改上游逻辑 | 不修复上游 bug，不修改已有 if/else 分支 |
| 新文件自由设计 | `_harmonyos_compat.py` 等新文件不受限 |
| 测试补丁独立 | 跳过平台限制测试，不影响运行时 |

### 2.3 补丁分类

完整列表见 `series`。按功能分为 5 组，共 104 个补丁：

| 组 | 分类 | 编号 | 补丁数 | 说明 |
|----|------|------|:------:|------|
| 1 | 构建系统 | 0093, 0100–0104 | 6 | configure.ac, configure, config.guess/sub, Makefile.pre.in, setup.py |
| 2 | C 源码 | 0001, 0094–0099 | 7 | pythread.h, thread_pthread.h, 5 个 Modules/*.c, pylifecycle.c |
| 3 | 运行时库 | 0002–0015, 0091, 0092 | 16 | 子进程兼容层、multiprocessing、路径、venv、uuid 等 |
| 4 | 测试数据 | 0016–0039 | 24 | Lib/test/data/ 下的编码表、归一化测试等数据文件 |
| 5 | 测试适配 | 0040–0090 | 51 | Lib/test/test_*.py 平台限制测试 skip/filter |

**核心补丁（组 1-3）：29 个** — 编译和运行所必需
**测试补丁（组 4-5）：75 个** — 仅运行 regrtest 时需要

### 2.4 核心适配点

#### musl BIND_NOW（组 1, configure.ac + Makefile.pre.in）

musl 默认 `BIND_NOW`，扩展模块必须链接 `libpython`：
- `LDSHARED = $(CC) -shared -L. -lpython$(LDVERSION)` （扩展模块）
- `BLDSHARED = $(CC) -shared` （libpython 本身，不能链接自己）

#### HMDFS 大小写不敏感（组 1, Makefile.pre.in）

`BUILDPYTHON=python` 与源码 `Python/` 冲突 → 改为 `python$(VERSION)`

#### HMDFS 不支持 symlink（组 3, venv/__init__.py）

`os.symlink()` 100% 失败 → `makedirs()` 降级。
> ⚠️ `ln -s` 在 HMDFS 上不会报错，但产生的不是真正的符号链接（文件名带随机后缀），
> 后续 `readlink()` 返回非预期内容。所有 symlink 操作必须用 copy 降级。

#### 硬链接不可用（组 1, Makefile.pre.in）

`HARDLINK = cp -p`，`LN_FORCE = rm -f && ln -s`（toybox `ln -sf` 有 bug）

#### HMDFS 符号链接不可跟踪（组 1, Makefile.pre.in sharedinstall）

`make install` 创建的 `libpython3.9.so → libpython3.9.so.1.0` 无效
→ 用 `$(HARDLINK)` 替代 `$(LN_FORCE)` 复制

#### SELinux 域转换（组 3, subprocess + _bootsubprocess）

`fork() + execve()` 执行 SDK 工具被拦截 → `_use_posix_spawn()` 返回 True
→ `posix_spawn()` 路径不受限制，pip install / clang 编译正常

#### posix_spawn 稳定路径（组 3, subprocess.py）

musl 的 `posix_spawn()` 实现质量良好 → 替代 fork+exec 作为默认子进程路径

#### HAVE_LIBUUID 强制定义（组 1, configure.ac）

`configure.ac` 中添加 `AC_DEFINE(HAVE_LIBUUID, 1, [...])` 强制定义，
确保 `pyconfig.h` 中 `HAVE_LIBUUID` 存在。
**构建后必须验证**：`grep HAVE_LIBUUID pyconfig.h` 应返回匹配行。

---

## 三、configure 参数

```bash
./configure --prefix=$HOME/usr/local \
  --disable-ipv6 \              # HarmonyOS 无 IPv6
  ac_cv_file__dev_ptmx=no \     # /dev/ptmx 被 Hmmac MAC 策略阻止
  ac_cv_file__dev_ptc=no \      # 无 /dev/ptc
  --enable-shared               # 生成 libpython3.9.so（扩展模块需要）
```

> ⚠️ **不要使用 `--enable-optimizations`（PGO）**。PGO 需要 instrumented build + 二次运行 profile
> 收集，在 HarmonyOS 上不工作（`make profile-opt` 阶段运行 instrumented binary 会触发 SIGSYS 或
> MAC 策略拒绝），且耗时翻倍但无实际收益。

---

## 四、构建注意事项

| 问题 | 症状 | 解决 |
|------|------|------|
| **PGO 不工作** | `--enable-optimizations` 构建失败或卡死 | 不要使用该选项 |
| **增量编译丢失 .so** | 修改后重新 `make`，部分 .so 未重新链接 | **必须 `make clean && make`**，增量编译可能跳过链接步骤 |
| **HAVE_LIBUUID 缺失** | uuid 模块编译异常 | configure 后检查 `grep HAVE_LIBUUID pyconfig.h` |
| gettext 空壳 | `_localemodule.c` 编译失败 | `CPPFLAGS="-I$HOME/usr/local/include"` |
| HMDFS 大小写 | `ld.lld: python: Is a directory` | 补丁自动处理 `BUILDPYTHON` |
| HMDFS symlink | `ln -s` 产生随机后缀文件 | 补丁自动替换为 `cp -p` |
| /tmp 只读 | configure/Python 写临时文件失败 | `export TMPDIR=$HOME/tmp` |
| ELF 签名 | 修改后 `Operation not permitted` | 重新签名（见 knowledge/packaging.md） |
| autoconf 版本 | configure 检测结果不一致 | 修改 configure.ac 后 `autoconf` 重新生成 |
| libffi ctypes | `test_ctypes` 多 ERROR | 升级 libffi 到 3.5.2（closure W^X 修复） |
| **patch exit code** | HMDFS 上 `patch -p1` fstat 异常导致 exit code 不可靠 | 必须从 tgz 全新解压后打补丁，检查输出而非 exit code |

### 关键构建流程提示

```bash
# ✅ 正确：全新解压 → 打补丁 → 构建
tar -xzf Python-3.9.25.tgz -C /build
cd /build/Python-3.9.25
# ... 应用 104 个补丁 ...
autoconf && ./configure ... && make -j$(nproc)

# ❌ 错误：在已有编译产物上增量打补丁
# HMDFS 不支持 symlink，已有 .so 链接可能被破坏

# ❌ 错误：修改后直接 make（不 clean）
# 增量编译可能丢失 .so 链接步骤，导致模块找不到
make clean && make  # 必须如此
```

---

## 五、测试结果

> **测试日期**: 2026-03-30
> **测试平台**: HarmonyOS-HongMeng_Kernel_1.11.0-aarch64-64bit-ELF, musl libc, Clang 15.0.4
> **Python**: CPython 3.9.25 (main, Mar 30 2026)
> **测试命令**: `LD_LIBRARY_PATH=. make test`

| 指标 | 数值 |
|------|------|
| 总测试 | 425 |
| 通过 | **384 (90.4%)** |
| 失败 | 8 |
| 跳过 | 33 |
| 完成率 | 100%（全部跑完） |

### 与 3.9.0 对比

| 指标 | 3.9.25 | 3.9.0 v52 | 变化 |
|------|--------|-----------|------|
| 通过 | **384** | 364 | **+20 ✅** |
| 失败 | **8** | 39 | **-31 ✅** |
| 跳过 | 33 | 20 | +13 |
| 通过率 | **90.4%** | 85.6% | **+4.8% ✅** |

### 失败测试（8 个）

| 测试 | 根因 | 来源 |
|------|------|------|
| test_posix | symlink 禁止 + chown 不生效 + sched_setscheduler 未实现 + pwd 缺用户（8 errors, 2 failures） | 3.9.0 遗留 |
| test_posixpath | symlink 禁止 → realpath 测试全部失败（23 errors, 1 failure） | 3.9.0 遗留 |
| test_socket | UDPLITE 不支持(24) + AF_UNIX 行为差异(3)（26 errors, 1 failure） | 3.9.0 遗留 |
| test_tarfile | mkfifo 不支持 + 权限设置不生效 | 3.9.0 遗留 |
| test_shutil | copyfile_nonexistent_dir 路径行为差异 | 3.9.0 遗留 |
| test_getpass | pwd.getpwuid 找不到当前 uid | 3.9.0 遗留 |
| test_httpservers | IPv6 `::1` DNS 解析失败 | 3.9.0 遗留 |
| test_time | 首次运行 SIGSYS 崩溃（内核 syscall 不支持，返回 SIGSYS 而非 EPERM） | 3.9.0 遗留 |

### 跳过测试分类（33 个）

| 类别 | 测试数 | 说明 |
|------|:------:|------|
| GUI (Tcl/Tk) | 7 | test_tcl, test_tix, test_tk, test_ttk_guionly, test_ttk_textonly, test_turtle, test_idle |
| Windows 专用 | 5 | test_winconsoleio, test_winreg, test_winsound, test_startfile, test_msilib |
| HarmonyOS 策略限制 | 6 | test_openpty, test_pty, test_signal, test_ioctl, test_devpoll, test_kqueue |
| HarmonyOS 系统差异 | 5 | test_c_locale_coercion, test_locale, test_format, test_embed, test_distutils |
| 多进程限制 | 3 | test_multiprocessing_fork, test_multiprocessing_forkserver, test_multiprocessing_spawn |
| 缺少 nis/spwd | 2 | test_nis, test_spwd |
| 缺少音频 | 1 | test_ossaudiodev |
| 其他 | 4 | test_dbm_dumb, test_netrc, test_uu, test_zipfile64, test_gdb, test_time(re-run) |

详见 `reports/REGRTEST_V1_ANALYSIS.md`。

---

## 六、与 3.9.0 的差异

### 6.1 补丁生成方式

| 项目 | 3.9.0 | 3.9.25 |
|------|-------|--------|
| 补丁管理 | quilt（series + .pc 目录） | patch -p1（series 文件记录顺序） |
| 生成方法 | 手动编写 + quilt refresh | 三目录 diff 法（clean vs patched） |
| 补丁格式 | quilt 标准 | `diff -ruN a/ b/` |
| 补丁总数 | 78 | **104** |

### 6.2 补丁数量变化

| 组 | 3.9.0 | 3.9.25 | 说明 |
|----|:------:|:------:|------|
| 构建系统 | 5 | 6 | 新增 autoconf 生成的 configure 脚本 |
| C 源码 | 7 | 7 | 结构相同 |
| 运行时库 | 15 | 16 | 新增 uuid.py 适配 |
| 测试数据 | 0 | **24** | 3.9.25 新增编码表等数据文件 diff（文件权限/行尾差异） |
| 测试适配 | 51 | 51 | 数量相同，内容有调整 |
| **合计** | **78** | **104** | |

### 6.3 上游改进（无需补丁的部分）

3.9.0→3.9.25 上游已修复的问题，3.9.25 中无需对应补丁：

- shutil sendfile 适配（上游已修复）
- pylifecycle fd 验证（上游已修复）
- 部分 subprocess.py 改进（上游已有，补丁范围缩小）

### 6.4 新增适配

| 补丁 | 说明 |
|------|------|
| 0091: Lib/uuid.py | `/etc/fstab` 路径适配（HarmonyOS 无此文件） |
| 0081: test_concurrent_futures | 新增 forkserver 排除（3.9.25 forkserver 实现变化触发 OHOS 限制） |
| 0082: test_curses | 新增 test_putwin 跳过（MAC 策略阻止写入临时文件） |

### 6.5 测试通过率提升

3.9.25 通过 **90.4%**（384/425），相比 3.9.0 的 85.6%（364/425）提升 **4.8 个百分点**。
主要原因：
- 上游 bug 修复减少了因 Python 自身问题导致的失败
- 补丁适配更精准（三目录法确保 patch clean vs patched 精确匹配）
- 新增 forkserver 和 curses 跳过补丁消除了 2 个平台兼容失败

---

## 七、已知限制

| 限制 | 说明 | 影响 | 临时方案 |
|------|------|------|----------|
| **HMDFS 不支持 symlink** | `os.symlink()` 不报错但产生非预期文件 | venv 创建、make install 软链接失败 | 补丁降级为 copy/makedirs |
| **HMDFS 大小写不敏感** | `python` 与 `Python/` 目录冲突 | 构建系统 `BUILDPYTHON` 命名冲突 | 补丁改为 `python$(VERSION)` |
| **/tmp 只读** | 系统临时目录不可写 | configure、Python tempfile 失败 | `export TMPDIR=$HOME/tmp` |
| **/dev/ptmx 不可访问** | MAC 策略阻止 | pty 模块不可用 | `ac_cv_file__dev_ptmx=no` |
| **PGO 不工作** | instrumented binary 触发 SIGSYS | 不能使用 `--enable-optimizations` | 使用 `-O2` 编译即可 |
| **无 IPv6** | 内核/网络栈不支持 | socket IPv6 测试失败 | `--disable-ipv6` |
| **SIGSYS 崩溃** | 不支持的 syscall 返回 SIGSYS 而非 EPERM | test_time 首次运行崩溃 | 无（内核限制） |
| **SELinux 域限制** | adhoc_bin 域无法 fork/exec SDK 工具 | pip install 需 posix_spawn 降级 | 补丁自动处理 |
| **pwd 缺用户数据** | `/etc/passwd` 无当前用户条目 | test_getpass、pwd.getpwuid 失败 | 无 |
| **增量编译不可靠** | make 不重新链接部分 .so | 修改后 make 可能产生过时模块 | **始终 `make clean && make`** |
| **patch exit code 不可靠** | HMDFS fstat 问题 | `patch -p1` 返回码可能不反映实际状态 | 检查 patch 输出而非 exit code |

---

## 八、相关文件

| 文件 | 用途 |
|------|------|
| `patches/` | 104 个适配补丁（三目录 diff 法生成） |
| `series` | 补丁应用顺序（5 组，按编号顺序） |
| `manifest.yaml` | 完整元数据（构建配置、补丁分类、测试结果） |
| `reports/REGRTEST_V1_ANALYSIS.md` | regrtest v1 测试详细分析 |

---

*Python 3.9.25 HarmonyOS 适配 — OpenHarmony PC Developer 社区*
