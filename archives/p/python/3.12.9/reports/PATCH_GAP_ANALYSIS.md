# Python 3.12.9 vs 3.9.25 补丁差距分析报告

**生成日期**: 2026-03-31  
**分析对象**: Python 3.9.25 (72 补丁) vs Python 3.12.9 (21 补丁)  
**3.9.25 状态**: 编译成功，380/425 测试通过  
**3.12.9 状态**: 21 个补丁已准备，尚未编译验证

---

## 1. 概览统计

| 类别 | 数量 | 说明 |
|------|------|------|
| 3.9 总补丁数 | 72 | 72 个独立补丁 |
| 3.12 已覆盖 | 21 (映射 3.9 的 21 个) | 含 0020 聚合了多个 3.9 补丁 |
| 3.12 不需要 | 4 | 文件已移除/功能已替代 |
| **3.12 需要补充** | **2 非测试 + ~41 测试** | 见下方详细分析 |
| 3.12 新增问题 | 3 | 3.12 特有的潜在问题 |

---

## 2. 3.12 已覆盖的 3.9 补丁映射表 ✅

以下 3.9 补丁在 3.12 中已有对应覆盖（含精确匹配或功能等价）：

### 2.1 平台检测 & 构建系统 (Phase 2A)

| 3.9 补丁 | 3.9 描述 | 3.12 补丁 | 状态 |
|----------|---------|----------|------|
| 0069 | config.guess - HarmonyOS 识别 | 0001 | ✅ 等价 |
| 0070 | config.sub - HarmonyOS 识别 | 0002 | ✅ 等价 |
| 0071 | configure.ac - MACHDEP=ohos | 0003 | ✅ 增强版（含更多检测） |

### 2.2 构建修复 (Phase 2B)

| 3.9 补丁 | 3.9 描述 | 3.12 补丁 | 状态 |
|----------|---------|----------|------|
| 0063 | Makefile.pre.in - ln 修复 | 0004 | ✅ 等价 |
| 0072 | setup.py - SDK sysroot | 0005 | ✅ 替代（Setup.stdlib.in 取代 setup.py） |

### 2.3 C 扩展模块 (Phase 2C)

| 3.9 补丁 | 3.9 描述 | 3.12 补丁 | 状态 |
|----------|---------|----------|------|
| 0001+0068 | pythread.h + thread_pthread.h - PY_HAVE_THREAD_NATIVE_ID | 0006+0007 | ✅ 拆分为两个补丁 |
| 0064 | _posixsubprocess.c - FD dir /dev/fd | 0008 | ✅ 等价 |
| 0066 | timemodule.c - musl timezone 修复 | 0009 | ✅ 等价 |
| 0065a | posixmodule.c - cpu_count (sysconf) | 0010 | ✅ 等价 |
| 0065b | posixmodule.c - fallocate __OHOS__ | 0019 | ✅ 等价（3.12 新增独立补丁） |

### 2.4 Python 标准库核心 (Phase 2D)

| 3.9 补丁 | 3.9 描述 | 3.12 补丁 | 状态 |
|----------|---------|----------|------|
| 0014 | sysconfig.py - get_platform 扩展 | 0011 | ✅ 等价 |
| 0010 | posixpath.py - defpath 设置 | 0012 | ✅ 等价 |
| 0013 | subprocess.py - posix_spawn 适配 | 0013 | ✅ 等价（3.12 版本更大） |
| 0003 | _harmonyos_compat.py - 兼容层模块 | 0014 | ✅ 等价 |
| 0012 | site.py - 加载兼容层 | 0015 | ✅ 等价 |
| 0008 | multiprocessing/context.py - spawn 默认 | 0016 | ✅ 等价 |
| 0009 | multiprocessing/util.py - abstract socket | 0017 | ✅ 等价 |
| 0062 | venv/__init__.py - symlink 修复 | 0018 | ✅ 等价 |

### 2.5 聚合补丁 (Phase 2E)

3.12 的 **0020** 补丁将多个 3.9 独立补丁聚合为一个：

| 3.9 补丁 | 3.9 描述 | 覆盖状态 |
|----------|---------|---------|
| 0067 | pylifecycle.c - is_valid_fd __OHOS__ | ✅ 已覆盖（0020 包含） |
| 0011 | shutil.py - sendfile "ohos" | ✅ 已覆盖（0020 包含） |
| 0015 | tempfile.py - OHOS 临时目录 | ✅ 已覆盖（0020 包含） |
| 0061 | uuid.py - /system/bin 路径 | ✅ 已覆盖（0020 包含） |
| (新增) | configure.ac - lchmod 跳过 | ✅ 已覆盖（0020 包含） |
| (新增) | configure - lchmod 跳过 | ✅ 已覆盖（0020 包含） |

### 2.6 HarmonyOS 特有修复 (Phase 2F)

| 3.9 补丁 | 3.9 描述 | 3.12 补丁 | 状态 |
|----------|---------|----------|------|
| (新增) | Makefile.pre.in - HMDFS symlink → HARDLINK | 0021 | ✅ 新增 |

---

## 3. 3.12 不需要的 3.9 补丁 ⏭️

| 3.9 补丁 | 3.9 描述 | 不需要的原因 |
|----------|---------|------------|
| 0002 | Lib/_bootsubprocess.py | **文件已移除**：3.12 中不再有此文件，subprocess 启动机制已重构 |
| 0006 | Lib/distutils/spawn.py | **distutils 已移除**：Python 3.12 正式移除 distutils，功能由 setuptools 替代 |
| 0007 | Lib/distutils/util.py | **distutils 已移除**：同上 |
| 0072 | setup.py - SDK sysroot | **setup.py 已移除**：3.12 不再使用 setup.py 构建扩展，由 Makefile + configure + Setup.stdlib.in 替代，3.12 0005 补丁提供等价功能 |

---

## 4. 3.12 需要补充的补丁 ❌

### 4.1 非测试补丁（P1 运行时必须）

#### ❌ 4.1.1 compileall.py - HMDFS hardlink 回退

- **3.9 补丁**: 0004
- **优先级**: **P1** (运行时，影响 compileall 和 pip 安装场景)
- **状态**: **未覆盖** - 3.12.9 源码 `Lib/compileall.py` 第 252-253 行仍然直接使用 `os.unlink()` + `os.link()`，没有 HMDFS 回退逻辑
- **影响**: 在 HMDFS 文件系统上，`os.link()` 返回 `EPERM`，导致使用 `--hardlink-dupes` 选项时 `compileall` 崩溃
- **需补充的修改**:

```python
# Lib/compileall.py - 需要在文件顶部添加:
import shutil  # 新增

# 第 249-253 行修改为:
                    if index > 0 and hardlink_dupes:
                        previous_cfile = opt_cfiles[optimize[index - 1]]
                        if filecmp.cmp(cfile, previous_cfile, shallow=False):
                            try:
                                os.unlink(cfile)
                                os.link(previous_cfile, cfile)
                            except OSError:
                                # HarmonyOS HMDFS does not support
                                # hardlink(2). Fall back to file copy
                                # so that deduplicated pyc files are
                                # still produced (just not hardlinked).
                                if sys.platform == 'ohos':
                                    shutil.copy2(previous_cfile, cfile)
                                else:
                                    raise
```

#### ❌ 4.1.2 ctypes/util.py - 无 /sbin/ldconfig 保护

- **3.9 补丁**: 0005
- **优先级**: **P1** (运行时，影响 ctypes 查找共享库)
- **状态**: **未覆盖** - 3.12.9 源码 `Lib/ctypes/util.py` 第 273 行 `_findSoname_ldconfig()` 函数直接调用 `/sbin/ldconfig -p`，无 OHOS 保护
- **影响**: HarmonyOS 没有 `/sbin/ldconfig`，调用会抛出 `FileNotFoundError`，导致 `ctypes.util.find_library()` 异常
- **需补充的修改**:

```python
# Lib/ctypes/util.py - _findSoname_ldconfig 函数开头添加:
        def _findSoname_ldconfig(name):
            # HarmonyOS: no /sbin/ldconfig, skip to avoid SubprocessError
            if sys.platform.startswith(('ohos', 'harmonyos')):
                return None
            import struct
            # ... 原有代码 ...
```

### 4.2 测试补丁（P2 测试修复）

以下 3.9 的 45 个测试补丁（0016-0060）在 3.12 中需要适配移植。

#### 4.2.1 不再适用的测试补丁（文件已移除）

| 3.9 补丁 | 测试文件 | 原因 |
|----------|---------|------|
| 0024 | test_distutils.py | distutils 已从 3.12 移除 |

#### 4.2.2 结构变化的测试（需适配包结构）

| 3.9 补丁 | 3.9 测试 | 3.12 测试路径 | 适配说明 |
|----------|---------|-------------|---------|
| 0021 | test_concurrent_futures.py (文件) | test_concurrent_futures/ (包) | 需在 `__init__.py` 中添加 forkserver 移除逻辑 |
| 0035 | test_multiprocessing_fork.py (文件) | test_multiprocessing_fork/ (包) | 需在 `__init__.py` 顶部添加模块级 skip |
| 0036 | test_multiprocessing_forkserver.py (文件) | test_multiprocessing_forkserver/ (包) | 需在 `__init__.py` 顶部添加模块级 skip |
| 0037 | test_multiprocessing_spawn.py (文件) | test_multiprocessing_spawn/ (包) | 需在 `__init__.py` 顶部添加模块级 skip |

#### 4.2.3 可直接移植的测试补丁（需调整行号）

以下测试补丁的核心逻辑（skip 装饰器/模块级 skip）在 3.12 中仍然需要。由于 3.12 测试代码有变更，需要重新定位代码位置：

| 3.9 补丁 | 测试文件 | 跳过原因分类 | 核心修改 |
|----------|---------|------------|---------|
| 0016 | test_argparse.py | HMDFS chmod 无效 | 添加 `@skipIf(ohos)` 到 TestFileTypeW |
| 0017 | test_asyncio/test_events.py | /dev/ptmx MAC 策略 | 添加 `_skip_no_ptmx` 到 pty 测试 |
| 0018 | test_c_locale_coercion.py | OHOS 强制 UTF-8 | 模块级 skip |
| 0019 | test_cmd_line.py | 隔离模式/warning 差异 | 多个测试方法添加 `@skipIf(ohos)` |
| 0020 | test_compileall.py | HMDFS 不支持 hardlink | 添加 `_check_hardlink()` + skip |
| 0022 | test_curses.py | putwin() MAC 策略 | 添加 `@skipIf(ohos)` |
| 0023 | test_dbm_dumb.py | 通用模块级 skip | 模块级 skip |
| 0025 | test_embed.py | _testembed 未编译 | 模块级 skip |
| 0026 | test_fcntl.py | F_GETLK64 不支持 | 添加 `@skipIf(ohos)` |
| 0027 | test_format.py | locale 格式化差异 | 模块级 skip |
| 0028 | test_httpservers.py | HMDFS chmod 无效 | 修改 chmod 条件检查 |
| 0029 | test_import/__init__.py | HMDFS 权限差异 | 多个测试添加 `@skipIf(ohos)` |
| 0030 | test_importlib/test_zip.py | entry_points 不兼容 | 添加 skip 装饰器 |
| 0031 | test_ioctl.py | pty 不可用 | 添加 `@skipIf(ohos)` |
| 0032 | test_locale.py | locale 支持不完整 | 模块级 skip |
| 0033 | test_mailbox.py | umask 权限差异 | 多个类添加 `@skipIf(ohos)` |
| 0034 | test_mmap.py | mmap PROT 不支持 | 类级 `@skipIf(ohos)` |
| 0038 | test_netrc.py | uid 不匹配 | 类级 `@skipIf(ohos)` |
| 0039 | test_openpty.py | openpty PermissionError | 模块级 skip |
| 0040 | test_os.py | 多种问题（权限/setreuid/chroot/listdir/sendfile/openpty） | 12+ 处 skip |
| 0041 | test_pathlib.py | HMDFS 权限/chmod/大小写 | 10+ 处 skip |
| 0042 | test_peg_generator/test_c_parser.py | distutils.spawn 管道 bug | 类级 `@skipIf(ohos)` |
| 0043 | test_posix.py | fallocate 不支持 | 添加 `@skipIf(ohos)` |
| 0044 | test_posixpath.py | uid 不在 passwd | 添加 `@skipIf(ohos)` |
| 0045 | test_pty.py | pty 不可用 | 模块级 skip |
| 0046 | test_py_compile.py | HMDFS 只读无效 | 两个类添加 `@skipIf(ohos)` |
| 0047 | test_readline.py | pty 不可用 | 模块级 + 类级 skip |
| 0048 | test_selectors.py | fd set 大小限制 | 添加 `@skipIf(ohos)` |
| 0049 | test_shutil.py | chmod/chown 无效 | 多处添加 `@skipIf(ohos)` |
| 0050 | test_signal.py | 信号处理差异 | 模块级 skip |
| 0051 | test_socket.py | UDPLITE 不支持 | 多个类添加 `@skipIf(ohos)` |
| 0052 | test_stat.py | umask 目录权限差异 | 两个类添加 `@skipIf(ohos)` |
| 0053 | test_strptime.py | strftime %Z 空字符串 | 多个方法添加 `@skipIf(ohos)` |
| 0054 | test_subprocess.py | fd 操作受限 + SIGSYS | 12+ 处 skip |
| 0055 | test_tarfile.py | umask 权限差异 | 多处添加 `@skipIf(ohos)` |
| 0056 | test_tempfile.py | umask/mkstemp/mkdir | 多个类添加 `@skipIf(ohos)` |
| 0057 | test_time.py | clock_gettime/clock_settime SIGSYS | 添加安全检测 + skip |
| 0058 | test_uu.py | 通用模块级 skip | 模块级 skip |
| 0059 | test_venv.py | symlink/bash 差异 | 多处修改 |
| 0060 | test_zoneinfo/test_zoneinfo.py | tzdata 版本差异 | 添加 `@skipIf(ohos)` |

---

## 5. 3.12 新增的潜在问题 ⚠️

### ⚠️ 5.1 _hacl/_sha2 预编译库架构不匹配

- **问题**: 3.12 中 `_sha2` 模块依赖预编译的 `Modules/_hacl/libHacl_Hash_SHA2.a` 静态库
- **构建配置** (`Setup.stdlib.in` 第 98 行):
  ```
  _sha2 sha2module.c -I$(srcdir)/Modules/_hacl/include Modules/_hacl/libHacl_Hash_SHA2.a
  ```
- **风险**: 该 `.a` 文件可能是为 x86_64 Linux 预编译的，无法在 aarch64-linux-ohos 上链接
- **优先级**: **P0** (编译必须) — 如果 `.a` 文件架构不匹配，`_sha2` 模块编译失败， hashlib 的 SHA-224/SHA-256/SHA-384/SHA-512 将不可用
- **建议方案**: 
  1. 检查 `libHacl_Hash_SHA2.a` 是否包含 aarch64 目标文件: `ar t libHacl_Hash_SHA2.a && aarch64-linux-ohos-objdump -t libHacl_Hash_SHA2.a`
  2. 如果架构不匹配，需要从 `Hacl_Hash_SHA2.c` 源码重新编译为 HarmonyOS 目标架构

### ⚠️ 5.2 test_peg_generator 仍依赖 distutils.spawn

- **问题**: 3.12 的 `test_peg_generator/test_c_parser.py` 仍然使用 `distutils.spawn.find_executable()` 来查找编译器
- **3.9 补丁 0042** 已对此做了 HarmonyOS skip 处理
- **3.12 状态**: 虽然 3.12 移除了 distutils 包，但 test_peg_generator 中可能仍通过其他路径引用
- **优先级**: **P2** (仅影响测试)
- **建议**: 检查 3.12.9 的 `Lib/test/test_peg_generator/test_c_parser.py` 是否仍使用 distutils.spawn，如果是则需要添加 `@skipIf(ohos)`

### ⚠️ 5.3 configure.ac 中 lchmod 检测已覆盖但需确认 generated configure 同步

- **问题**: 3.12 的 0020 补丁修改了 `configure.ac` 和 `configure` 中 lchmod 检测，但 `configure` 是 autoconf 生成的文件
- **风险**: 如果手动编辑 `configure` 后再次运行 `autoconf`，修改会丢失
- **优先级**: **P0** (编译必须) — 如果 lchmod 被错误检测，编译可能失败
- **建议**: 确认 0020 补丁同时修改了 `configure.ac` 和 `configure`，且 `configure` 的修改不会被覆盖

---

## 6. 优先级排序

### P0 — 编译必须（不修复则编译失败）

| 编号 | 补丁 | 描述 |
|------|------|------|
| P0-1 | 检查 _sha2 | 确认 `libHacl_Hash_SHA2.a` 是否可在 HarmonyOS 上链接 |
| P0-2 | 确认 configure | 确认 lchmod 检测修改已正确应用于 generated configure |

### P1 — 运行时必须（不修复则功能异常）

| 编号 | 补丁 | 描述 | 建议补丁编号 |
|------|------|------|-------------|
| P1-1 | compileall.py | HMDFS hardlink 回退为 copy2 | **新增 0022** |
| P1-2 | ctypes/util.py | 无 /sbin/ldconfig 时跳过 | **新增 0023** |

### P2 — 测试修复（不修复则测试失败）

| 分类 | 数量 | 说明 |
|------|------|------|
| HMDFS 权限/chmod/umask | ~20 处 | HMDFS 不完全遵守 Unix 权限模型 |
| pty/ptmx 不可用 | ~8 处 | HarmonyOS MAC 策略限制 |
| 信号处理差异 | ~5 处 | setreuid/setregid 触发 SIGSYS |
| fd 操作受限 | ~8 处 | /proc/self/fd 不可用 |
| locale/编码差异 | ~4 处 | strcoll/strxfrm/formatting 不正确 |
| 其他 | ~6 处 | uid 不匹配/sendfile/UDPLITE 等 |

---

## 7. 行动建议

### 7.1 立即行动（编译前）

1. **检查 _sha2 架构兼容性**: 验证 `libHacl_Hash_SHA2.a` 是否包含 aarch64 目标文件，如果不兼容则需要从源码重新编译
2. **添加 P1 补丁**: 将 compileall.py 和 ctypes/util.py 补丁添加到 3.12.9 补丁系列

### 7.2 编译验证后

1. **移植测试补丁**: 由于 3.12 测试代码结构有变化，建议先编译成功后运行测试，根据实际失败情况逐个添加 skip
2. **优先处理高频失败类别**: HMDFS 权限问题和 pty 不可用是两大主要失败原因

### 7.3 3.12 vs 3.9 关键差异提示

- 3.12 不再使用 `setup.py`，扩展模块通过 `configure` + `Makefile` + `Setup.stdlib.in` 构建
- 3.12 测试结构从单一文件变为包（目录 + `__init__.py`），测试 skip 需要在正确位置添加
- 3.12 新增 `_hacl` 模块提供 hashlib 后端，需要特别关注预编译库兼容性
- 3.12 的 `os.sendfile()` 通过 `HAVE_SENDFILE` 配置检测控制，如果 HarmonyOS 不提供 sendfile 则自动禁用（不同于 3.9 需要手动 skip 测试）

---

*报告完成。建议优先处理 P0 和 P1 项，然后进行编译验证。*
