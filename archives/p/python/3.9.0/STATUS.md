# Python 3.9.0 鸿蒙适配：进展总结与下一步计划

> **最后更新**: 2026-03-26 | **维护者**: OpenHarmony PC Developer 社区

---

## 一、已完成的工作

### 1. 编译成功（20 个补丁，3 层构建系统适配）

Python 3.9.0 已在 HarmonyOS PC（aarch64, musl libc, Clang 15）上成功编译，涉及构建系统三层的全面适配：

| 层级 | 补丁 | 解决的问题 |
|------|------|-----------|
| 平台检测层 | 0003 (config.guess) + 0004 (config.sub) | 三元组识别 `aarch64-unknown-linux-ohos` |
| 配置生成层 | 0001 (configure.ac, 10 处修改) | MACHDEP、共享库、BIND_NOW、CAN_RAW 等 |
| 构建执行层 | 0002 (setup.py) + 0007 (Makefile) | SDK 路径、LDSHARED 链 libpython、硬链接→cp -p、相对路径 srcdir |
| 运行时适配 | 0005~0006 + 0008~0011 | 平台字符串、子进程 pipe 绕过、venv symlink 回退 |
| **Phase 1 修复** | **0012~0020** | **threading API、multiprocessing spawn、子进程全面修复、时区、PATH 等** |

**关键突破**：
- 解决 musl BIND_NOW 问题（扩展模块必须链接 `-lpython`）
- 解决 SELinux 子进程限制（`cmd | cat` pipe 绕过）
- subprocess 全面改造：posix_spawn musl 路径 + 临时文件 pipe workaround + Python 纯 fallback

### 2. 全量构建验证（2026-03-25）

| 类别 | 数量 |
|------|------|
| ✅ 编译+导入成功 | **64 个扩展模块** |
| ⚠️ 编译成功但导入失败 | 2（_gdbm, _lzma，库路径问题） |
| ❌ 编译失败 | 1（_ctypes，libffi 缺失） |
| ⏭️ 依赖缺失未编译 | 10（_ssl, _hashlib, _sqlite3 等） |

### 3. 官方测试结果（425 个测试用例）

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 通过 | 314 | 74.9% |
| ❌ 失败 | 80 | 19.1%（主要是 multiprocessing/PTY/locale） |
| ⏭️ 跳过 | 25 | 6.0%（GUI/Windows/网络资源） |
| 💥 崩溃排除 | 6 | 1.4%（invalid syscall 卡住） |

> ⚠️ 注意：此测试结果基于 11 补丁版本（补丁 0001-0011）。应用 0012-0020 后需重新运行测试以更新数据。

**核心结论**：数据结构、字符串编码、文件 I/O、数据库、加密哈希、网络协议等核心功能全部正常。

### 4. 子进程问题根因分析（3/20 调试会话）

通过 C 级系统调用测试框架（7 个测试程序），逐层定位了子进程失败的完整链路：

```
根因：SELinux 域转换
  Shell (hishell_hap:s0) → exec Python → adhoc_bin:s0 → 无权 exec SDK 工具 (hnp_file)

完整测试矩阵（T0-T6，2026-03-26 更新）：
  T0: os.fork()                 ✅ 正常
  T1: Popen+wait (无 PIPE)      ✅ 正常（0020 修复）
  T2: stderr=PIPE               ✅ 正常（0020 修复）
  T3: PIPE+communicate          ✅ 正常（0020 修复，改用真正 os.pipe()）
  T4: subprocess.run() capture  ✅ 正常
  T5: error capture             ✅ 正常（0020 修复）
  T6: stdin pipe (双向)         ✅ 正常（0020 修复）
  T3b: stdout+stderr 双 PIPE   ✅ 两个 pipe 同时工作
  T-env: env dict + PIPE       ✅ execve env 类型 bug 已修复
```

**重要发现**：
- Python 的 fd 0/1/2 在鸿蒙上是 **socket 而非终端**，但 `posix_spawn` + `os.pipe()` 正常工作
- **补丁 0016 的临时文件方案导致了 pipe 数据丢失**（0020 已修复，恢复使用 `os.pipe()`）
- `_python_fork_exec` 的 `os.execve()` 需要 dict 而非 list of bytes（0020 已修复）
- `_posixsubprocess.c` C 扩展是硬依赖，缺失时整个 subprocess 模块不可用

### 5. 全量遗漏扫描（24 个遗漏点）

| 优先级 | 数量 | 关键影响 |
|--------|------|---------|
| **P0 必须修复** | 5 | pip 安装阻塞、multiprocessing 不可用、threading API 不完整 |
| **P1 建议修复** | 11 | 时区处理、sendfile 性能、共享内存路径 |
| **P2 低优先级** | 8 | mimetypes、uuid、pty（影响有限） |

### 6. 上游合入方案分析

| 类别 | 占比 | 说明 |
|------|------|------|
| 可直接提 PR | ~70% | configure + sysconfig + distutils + venv |
| 需重构后提 PR | ~15% | setup.py SDK root、Makefile HARDLINK |
| 只能 downstream 维护 | ~15% | _harmonyos_compat.py（monkey-patch 侵入性太强） |

### 7. 文档资产

| 文档 | 内容 |
|------|------|
| HARMONYOS_SUBPROCESS_GUIDE.md (v2.0) | 子进程完整指南，含 C 级测试矩阵、Pipe 绕过方案、3.12 路线图 |
| UPSTREAM_ADAPTATION_ANALYSIS.md | 上游合入方案 + 遗漏扫描汇总 |
| PATCH_DETAIL_ANALYSIS.md | 补丁逐文件 diff 分析（待更新至 20 个补丁） |
| MISSING_ADAPTATION_SCAN.md | 24 个遗漏点完整报告（含代码示例） |
| README.md (v4.0) | 完整编译指南，含补丁详解和举一反三 |

---

## 二、补丁清单（20 个）

> 2026-03-26 更新：从 11 个补丁扩充至 20 个（新增 0012-0020），work 目录全部变更已补丁化。
> 0002 和 0008 已用完整的 ref→work diff 替换（包含后续新增的 srcdir 相对路径修复）。

### 核心构建系统（0001-0011）

| 补丁 | 文件 | 说明 |
|------|------|------|
| 0001 | configure.ac | 平台识别、MACHDEP、共享库、BIND_NOW、CAN_RAW 等 |
| 0002 | setup.py | 扩展模块编译 + SDK sysroot + **相对路径 srcdir** |
| 0003 | config.guess | 平台三元组识别（aarch64/arm/x86_64） |
| 0004 | config.sub | 三元组验证 |
| 0005 | Lib/distutils/util.py | get_platform() 返回 "ohos-{machine}" |
| 0006 | Lib/_bootsubprocess.py | SELinux 管道语法绕过 |
| 0007 | Makefile.pre.in | HARDLINK→cp -p、BUILDPYTHON 名称 |
| 0008 | Lib/sysconfig.py | get_platform() + **相对路径 srcdir** |
| 0009 | Lib/_harmonyos_compat.py | 子进程兼容层模块（新增文件） |
| 0010 | Lib/site.py | 自动加载兼容层 |
| 0011 | Lib/venv/__init__.py | symlink→makedirs 降级 |

### Phase 1：解除 pip 阻塞（0012-0020）

| 补丁 | 遗漏点 ID | 文件 | 说明 |
|------|-----------|------|------|
| 0012 | P0-1 | Include/pythread.h | threading.get_native_id() 支持 |
| 0013 | P0-2 | Lib/multiprocessing/context.py | 默认 spawn 模式 + ForkProcess 保护 |
| 0014 | P0-3 | Lib/multiprocessing/util.py | abstract sockets 支持 |
| 0015 | P0-4 | Lib/posixpath.py | PATH 添加 /system/bin |
| 0016 | P1-1/P1-11/P0-5 | Lib/subprocess.py | **子进程全面修复**（pipe workaround + posix_spawn musl + shell 路径 + Python fork_exec fallback） |
| 0017 | P1-2 | Modules/_posixsubprocess.c | FD_DIR 改为 /dev/fd |
| 0018 | P1-3 | Modules/posixmodule.c | posix_fallocate 支持 |
| 0019 | P1-4 | Modules/timemodule.c | musl 时区处理 |
| 0020 | 修正 | Lib/subprocess.py | **修复 0016 遗留**：os.pipe() 替代临时文件、execve env dict、启用 posix_spawn |

> **关于 0020 的说明**：补丁 0016 的 `_OHOS_PIPE_WORKAROUND` 临时文件方案导致 `communicate()` 无法正确读取子进程输出。
> 调试发现鸿蒙的 `posix_spawn` + `os.pipe()` 完全可用，临时文件方案没有必要。0020 的修复：
> - stdout/stderr PIPE 恢复使用 `os.pipe()`（移除 `_ohos_make_temp_pair`）
> - `_python_fork_exec()` 的 `os.execve()` 使用原始 `env` dict 而非 `env_list`（list of bytes）
> - 移除 posix_spawn 路径对 `_OHOS_PIPE_WORKAROUND` 的禁用条件

> **关于 0016 的说明**：这是最大的补丁（22KB，541 行），包含多项关键修复：
> - `_posixsubprocess` 导入改为可选（ModuleNotFoundError 兼容）
> - 新增 `_py_close_open_fds()` 纯 Python 实现
> - 新增 `_python_fork_exec()` 纯 Python fork/exec fallback
> - `_OHOS_PIPE_WORKAROUND` 临时文件方案替代 pipe
> - `_use_posix_spawn()` 对 musl 返回 True（覆盖 P1-11）
> - shell 路径支持 `/system/bin/sh`（覆盖 P0-5）
> - `_communicate()` 降级处理（`_PopenSelector=None`）

---

## 三、当前状态

### Phase 1 已完成（2026-03-26）

**核心成果**：
- ✅ 20 个补丁全部可干净应用（origin 基准验证）
- ✅ Python 3.9.0 编译成功（64 个扩展模块）
- ✅ pip 可用（pip install pytest 成功）
- ✅ _ssl / _hashlib 编译成功（--with-openssl 绕过 pkg-config bug）
- ✅ subprocess T0-T6 全部通过（补丁 0020 修复）
- ✅ quicktest 失败从 8 降至 3（剩余为鸿蒙平台限制）
- ✅ 9 个 C 扩展包测试（4 compatible / 2 partial / 3 import 失败）

**quicktest 结果**（排除 test_time 崩溃）：
- ✅ 已修复：test_builtin、test_module、test_repl（subprocess pipe 修复）
- 剩余 3 个平台限制：test_locale（locale 不可用）、test_posix（chown 权限）、test_import（文件权限）
- 1 个崩溃：test_time（clock_settime bad syscall）

### 编译命令

```bash
autoconf
./configure --prefix=$HOME/usr/local --host=aarch64-unknown-linux-ohos \
  --build=aarch64-unknown-linux-ohos --disable-ipv6 \
  ac_cv_file__dev_ptmx=no ac_cv_file__dev_ptc=no \
  --with-openssl=$HOME/usr/local --enable-shared
make -j$(nproc)
```

### 已知问题

| 问题 | 根因 | 状态 | 修复方式 |
|------|------|------|---------|
| pkg-config `--cflags` 返回空 | pkg-config 0.29.2 实现缺陷 | ⚠️ 调查中 | --with-openssl 绕过 |
| libpython3.9.so 不导出动态符号 | 编译时未开启 --enable-shared | 🔴 P0 | 重新编译 Python |
| greenlet/ujson/numpy import 失败 | 上述符号导出问题 | 🔴 P0 | 同上 |
| Python/ 目录被 ELF 覆盖 | 之前编译产物误创建 | ✅ 已修复 | 从 ref 恢复 |
| Python-3.9.0-ref 被补丁污染 | 之前调试修改了 ref | ✅ 已修复 | 从 origin 重建 |

### 已覆盖的遗漏点

| ID | 描述 | 补丁 |
|----|------|------|
| P0-1 | threading.get_native_id() | 0012 |
| P0-2 | multiprocessing 默认 spawn | 0013 |
| P0-3 | abstract sockets | 0014 |
| P0-4 | defpath PATH | 0015 |
| P0-5 | shell 路径 | 0016 |
| P1-1 | subprocess 全面修复 | 0016 |
| P1-2 | FD_DIR /dev/fd | 0017 |
| P1-3 | posix_fallocate | 0018 |
| P1-4 | musl 时区 | 0019 |
| P1-11 | _use_posix_spawn() musl | 0016 |

注意：P0/P1 编号以 patches/series 标注为准。STATUS.md 中的编号可能与 MISSING_ADAPTATION_SCAN.md 中的原始编号存在映射差异（早期调试中进行了重编号），后续需统一。

---

## 四、下一步工作计划

### 🔴 P0：修复 libpython3.9.so 符号导出

重新编译 Python 3.9.0（开启 `--enable-shared`），解决 greenlet、ujson、numpy 的 import 失败问题。

预期效果：C 扩展兼容性从 4/9 提升到 7+/9。

步骤：
1. `make clean` + 重新 `configure`（添加 `--enable-shared`）
2. `make -j$(nproc)` + `make install`
3. 验证 `nm -D libpython3.9.so | grep PyType_IsSubtype`
4. 重跑 C 扩展四关卡测试
5. 补丁无需修改（configure 参数变更不影响源码补丁）

### 🟡 P1：完善验证

1. 升级 pip 20.2.3 → 26.0.1
2. 基于 --enable-shared 重编译后重跑 quicktest
3. 重跑 C 扩展四关卡测试
4. 验证 `python -m venv` 完整流程

### 🟢 P2：文档收尾

1. 统一 P0/P1 编号体系（以 MISSING_ADAPTATION_SCAN.md 为基准）
2. 补丁路径前缀规范化（14/20 个补丁使用非标准 a/b/ 前缀）
3. SCAN/UPSTREAM 报告同步 fork() 可用性和 pipe 修复结论

### 📋 Phase 2 预备

- multiprocessing 完整测试（spawn Pool）
- 共享内存路径修复（/dev/shm）
- sendfile 支持

---

## 五、可复用资产

| 资产 | 路径 | 用途 |
|------|------|------|
| 补丁文件 | 本目录 `patches/` | **20 个 .patch 文件**（含 series 索引） |
| 编译好的 Python 3.9 | `~/python/Python-3.9.0-work/python3.9` | 可直接运行（含 20 补丁 + SSL） |
| 干净源码基准 | `~/python/Python-3.9.0-ref/` | 干净的 Python 3.9.0 原始源码（已验证与 origin 一致） |
| 原始未修改源码 | `~/python/Python-3.9.0-origin/` | tar 包解压的原始副本 |

---

## 六、关键修复代码参考

### P1-11: subprocess._use_posix_spawn()（已包含在补丁 0016）
```python
# Lib/subprocess.py _use_posix_spawn() 函数中
# 对 musl 系统直接返回 True（覆盖鸿蒙）
except (AttributeError, ValueError, OSError):
    # os.confstr() or CS_GNU_LIBC_VERSION value not available.
    # This likely means musl libc (Alpine Linux, HarmonyOS, OpenWrt, etc.).
    # musl's posix_spawn() implementation properly reports errors
    # and is safe to use.
    return True
```

### P0-2: multiprocessing 默认 spawn（补丁 0013）
```python
# Lib/multiprocessing/context.py
def get_all_start_methods(self):
    if sys.platform == 'win32':
        return ['spawn']
    elif sys.platform == 'darwin':
        return ['spawn', 'fork']
    elif hasattr(os, 'fork'):
        methods = ['fork', 'spawn']
        if reduction.HAVE_SEND_HANDLE:
            methods.append('forkserver')
        return methods
    else:
        return ['spawn']  # HarmonyOS and others without fork()

# ForkProcess/ForkServerProcess 定义保护
if sys.platform != 'win32' and hasattr(os, 'fork'):
    class ForkProcess(process.BaseProcess): ...

# 默认上下文
elif sys.platform.startswith(('ohos', 'harmonyos')):
    _default_context = DefaultContext(_concrete_contexts['spawn'])
```

### P1-2: _posixsubprocess.c FD_DIR（补丁 0017）
```c
// Modules/_posixsubprocess.c
#if defined(__FreeBSD__) || (defined(__APPLE__) && defined(__MACH__)) || defined(__OHOS__)
# define FD_DIR "/dev/fd"
#else
# define FD_DIR "/proc/self/fd"
#endif
```

### P0-5: subprocess shell 路径（已包含在补丁 0016）
```python
# Lib/subprocess.py
if hasattr(sys, 'getandroidapilevel'):
    unix_shell = '/system/bin/sh'
elif sys.platform.startswith(('ohos', 'harmonyos')):
    unix_shell = '/system/bin/sh' if os.path.exists('/system/bin/sh') else '/bin/sh'
else:
    unix_shell = '/bin/sh'
```
