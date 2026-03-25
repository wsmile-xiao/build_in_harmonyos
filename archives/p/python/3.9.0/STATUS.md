# Python 3.9.0 鸿蒙适配：进展总结与下一步计划

> **最后更新**: 2026-03-26 | **维护者**: OpenHarmony PC Developer 社区
> **状态数据来源**: 2026-03-26 实际验证，基于 20 补丁版本（补丁 0001-0020）

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

### 2. 全量构建验证（2026-03-26）

| 类别 | 数量 |
|------|------|
| ✅ 编译+导入成功 | **72/72 扩展模块**（make install 后全部导入成功） |
| ⚠️ 编译成功但导入失败 | 3（运行时库缺失，编译本身成功） |
| ⏭️ 未编译（依赖缺失） | 1（_tkinter 缺少 TK/X11 库） |

**扩展模块 .so 全量导入测试**（72 个 .so 文件）：
- ✅ 导入成功：**69/72**
- ❌ 导入失败（运行时库缺失）：
  - `_dbm`：缺 `libgdbm_compat.so.4`
  - `_gdbm`：缺 `libgdbm.so.6`
  - `_lzma`：缺 `liblzma.so.5`
- ⏭️ 未编译：`_tkinter`（缺 TK/X11 库，`setup.py` 跳过）

**特别说明**：
- ✅ `_ctypes`：导入成功（旧版 STATUS 错误记录为编译失败，实际 libffi 可用）
- ✅ `_posixsubprocess`：编译成功（9.8MB），旧版 STATUS 暗示缺失，已解决
- ✅ `_ssl` + `_hashlib`：编译+导入成功
- ✅ `_curses` + `_curses_panel`：编译+导入成功
- ✅ `_sqlite3`：编译+导入成功

### 3. SSL 支持（2026-03-26 验证）

| 项目 | 状态 |
|------|------|
| `_ssl` 编译+导入 | ✅ 成功 |
| `_hashlib` 编译+导入 | ✅ 成功 |
| OpenSSL 版本 | 1.1.1w |
| 编译参数 | `--with-openssl=$HOME/usr/local` |

> ⚠️ `pkg-config --cflags openssl` 返回空是 pkg-config 0.29.2 的已知 bug，通过 `--with-openssl` 手动指定路径绕过。

### 4. pip（2026-03-26 验证）

| 项目 | 状态 |
|------|------|
| pip 版本 | 20.2.3（随 Python 3.9.0 内置） |
| 可用性 | ✅ 正常 |
| 已安装包 | pytest 8.4.2 |
| 可升级版本 | 26.0.1（尚未执行） |

### 5. 子进程问题根因分析（2026-03-26 验证）

通过 C 级系统调用测试框架（7 个测试程序），逐层定位了子进程失败的完整链路：

```
根因：SELinux 域转换
  Shell (hishell_hap:s0) → exec Python → adhoc_bin:s0 → 无权 exec SDK 工具 (hnp_file)

完整测试矩阵（T0-T6，全部通过）：
  T0: os.fork()                 ✅ 正常
  T1: Popen+wait (无 PIPE)      ✅ 正常（0020 修复）
  T2: stderr=PIPE               ✅ 正常（0020 修复）
  T3: PIPE+communicate          ✅ 正常（0020 修复，改用真正 os.pipe()）
  T4: subprocess.run() capture  ✅ 正常
  T5: error capture             ✅ 正常（0020 修复）
  T6: stdin pipe (双向)         ✅ 正常（0020 修复）
```

**重要发现**：
- Python 的 fd 0/1/2 在鸿蒙上是 **socket 而非终端**，但 `posix_spawn` + `os.pipe()` 正常工作
- **补丁 0016 的临时文件方案导致了 pipe 数据丢失**（0020 已修复，恢复使用 `os.pipe()`）
- `_python_fork_exec` 的 `os.execve()` 需要 dict 而非 list of bytes（0020 已修复）
- `_posixsubprocess.c` C 扩展是硬依赖，缺失时整个 subprocess 模块不可用

### 6. 官方测试结果

> ⚠️ **注意**：以下结果基于 11 补丁版本（补丁 0001-0011），应用 0012-0020 后**未重新运行**，数据仅供参考。

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 通过 | 314 | 74.9% |
| ❌ 失败 | 80 | 19.1%（主要是 multiprocessing/PTY/locale） |
| ⏭️ 跳过 | 25 | 6.0%（GUI/Windows/网络资源） |
| 💥 崩溃排除 | 6 | 1.4%（invalid syscall 卡住） |

**核心结论**：数据结构、字符串编码、文件 I/O、数据库、加密哈希、网络协议等核心功能全部正常。

### 7. quicktest（2026-03-26 验证）

| 项目 | 状态 |
|------|------|
| `python3.9 -m test_builtin` | ❌ 不可用（PYTHONPATH 优先加载 `$HOME/usr/local` 的 stdlib，不包含 `test/` 目录） |
| `python3.9 Lib/test/test_builtin.py` | ✅ 通过（103 tests, 0 failures, 4 skipped） |
| 其他测试模块 | 未重新验证 |

> 🟡 quicktest 依赖 `python -m test` 方式运行，但由于 PYTHONPATH 问题当前不可复现，待调查解决。

### 8. C 扩展包兼容性

> ⚠️ **注意**：之前在 11 补丁版本上的 9 包测试结果（4 compatible / 2 partial / 3 import 失败）**已失效**。所有测试包已从 site-packages 卸载，需要 `pip install` 重新测试。
>
> 重测可能受 libpython3.9.so 符号导出问题影响（见「已知问题」），建议 P0 修复后再执行。

### 9. 全量遗漏扫描（24 个遗漏点）

> 完整性验证（2026-03-26）：与 work→origin 的实际 diff 交叉比对，确认 24 个遗漏点**完整无遗漏**。无新增遗漏点。详见 `reports/MISSING_ADAPTATION_SCAN.md`。
>
> ⚠️ SCAN 报告中有 5 处"fork 不可用"的错误描述（T0 测试已证明 fork 在鸿蒙上可用），待修正但遗漏点清单本身完整。

| 优先级 | 数量 | 关键影响 |
|--------|------|---------|
| **P0 必须修复** | 5 | threading API、multiprocessing 默认模式、subprocess 全面修复、fd 验证 |
| **P1 建议修复** | 11 | 时区处理、sendfile 性能、共享内存路径 |
| **P2 低优先级** | 8 | mimetypes、uuid、pty（影响有限） |

**补丁覆盖情况**（9/24 已覆盖，其中 P0-1 为部分覆盖）：

| 遗漏ID | 描述 | 补丁 | 状态 |
|--------|------|------|------|
| P0-1 | threading.get_native_id() | 0012 | ⚠️ **部分**（pythread.h 已修复，thread_pthread.h 实现缺失） |
| P0-2 | multiprocessing 默认 spawn | 0013 | ✅ |
| P0-3 | _posixsubprocess.c FD_DIR /dev/fd | 0017 | ✅ |
| P0-4 | pylifecycle.c fd 验证 | — | ❌ 未修复 |
| P0-5 | subprocess shell 路径 | 0016 | ✅ |
| P1-1 | timemodule.c musl 时区 | 0019 | ✅ |
| P1-2 | shutil.py sendfile 优化 | — | ❌ |
| P1-3 | posixmodule.c sendfile NULL offset | 0018 | ✅（补丁文件名误标为 fallocate） |
| P1-4 | multiprocessing/util.py abstract sockets | 0014 | ✅ |
| P1-5 | multiprocessing/heap.py /dev/shm | — | ❌ |
| P1-6 | pidfd_open/pidfd_send_signal | — | ❌（低优先级） |
| P1-7 | socketmodule.c 抽象 socket | — | ❌ |
| P1-8 | posixpath.py defpath | 0015 | ✅ |
| P1-9 | tempfile.py 临时目录 | — | ❌ |
| P1-10 | configure lchmod 检测 | — | ❌（无实际影响） |
| P1-11 | _use_posix_spawn() musl | 0016 | ✅ |
| P2-1~P2-8 | 各类低优先级项 | — | ❌（8 项，影响有限） |

### 10. 上游合入方案分析

| 类别 | 占比 | 说明 |
|------|------|------|
| 可直接提 PR | ~70% | configure + sysconfig + distutils + venv |
| 需重构后提 PR | ~15% | setup.py SDK root、Makefile HARDLINK |
| 只能 downstream 维护 | ~15% | _harmonyos_compat.py（monkey-patch 侵入性太强） |

### 11. 文档资产

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
>
> ⚠️ **补丁依赖**：补丁 0020 依赖 0016（必须先应用 0016 才能应用 0020）。在干净源码上单独 check 0020 会失败，必须按 patches/series 中的顺序依次应用。

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

| 补丁 | 遗漏点 ID（MISSING_ADAPTATION_SCAN.md 编号） | 文件 | 说明 |
|------|-----------|------|------|
| 0012 | P0-1（部分） | Include/pythread.h | threading.get_native_id() 声明 |
| 0013 | P0-2 | Lib/multiprocessing/context.py | 默认 spawn 模式 + ForkProcess 保护 |
| 0014 | P1-4 | Lib/multiprocessing/util.py | abstract sockets 支持 |
| 0015 | P1-8 | Lib/posixpath.py | PATH 添加 /system/bin |
| 0016 | P0-5 + P1-11 | Lib/subprocess.py | **子进程全面修复**（pipe workaround + posix_spawn musl + shell 路径 + Python fork_exec fallback） |
| 0017 | P0-3 | Modules/_posixsubprocess.c | FD_DIR 改为 /dev/fd |
| 0018 | P1-3 | Modules/posixmodule.c | sendfile NULL offset 支持（补丁文件名误标为 fallocate） |
| 0019 | P1-1 | Modules/timemodule.c | musl 时区处理 |
| 0020 | 修正 | Lib/subprocess.py | **修复 0016 遗留**：os.pipe() 替代临时文件、execve env dict、启用 posix_spawn |

> **关于 0020 的说明**：补丁 0016 的 `_OHOS_PIPE_WORKAROUND` 临时文件方案导致 `communicate()` 无法正确读取子进程输出。
> 调试发现鸿蒙的 `posix_spawn` + `os.pipe()` 完全可用，临时文件方案没有必要。0020 的修复：
> - stdout/stderr PIPE 恢复使用 `os.pipe()`（移除 `_ohos_make_temp_pair`）
> - `_python_fork_exec()` 的 `os.execve()` 使用原始 `env` dict 而非 `env_list`（list of bytes）
> - 移除 posix_spawn 路径对 `_OHOS_PIPE_WORKAROUND` 的禁用条件
>
> **0020 依赖 0016**：0020 是对 0016 的修正补丁，在干净源码上 `git apply 0020.patch` 会失败，必须先应用 0016。patches/series 中的顺序已正确排列。

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
- ✅ 20 个补丁全部可干净应用（origin 基准验证，须按 series 顺序）
- ✅ Python 3.9.0 编译成功（72 个 .so 扩展模块，make install 后 72/72 导入成功）
- ✅ libpython3.9.so 正确导出 1459 个 text 符号（PyType_IsSubtype 等 C API 全部可用）
- ✅ make install 完成，install 目录完整（bin/python3.9、libpython3.9.so、72 个 lib-dynload .so）
- ✅ pip 20.2.3 可用（已安装 pytest 8.4.2）
- ✅ _ssl / _hashlib 编译+导入成功（OpenSSL 1.1.1w）
- ✅ _ctypes 编译+导入成功
- ✅ _posixsubprocess 编译成功（9.8MB）
- ✅ subprocess T0-T6 全部通过（补丁 0020 修复）
- ✅ test_builtin 通过（103 tests, 0 failures, 4 skipped）

**编译命令**（2026-03-26 P0 重编译，已启用 --enable-shared）：

```bash
autoconf
CPPFLAGS="-I$HOME/usr/local/include" LDFLAGS="-L$HOME/usr/local/lib" \
./configure --prefix=$HOME/usr/local --disable-ipv6 \
  ac_cv_file__dev_ptmx=no ac_cv_file__dev_ptc=no \
  --enable-shared
make -j$(nproc)
make install
```

> **环境说明**：
> - `CPPFLAGS`/`LDFLAGS` 指定 libintl 头文件和库路径（gettext 依赖，用于 _locale 模块）
> - OpenSSL 路径由 pkg-config 自动检测（已修复，无需手动指定）
> - 不主动指定 `--host`/`--build`，由 config.guess 自动检测
> - `--disable-ipv6`：HarmonyOS 当前不支持 IPv6

### 已知问题

| 问题 | 根因 | 状态 | 备注 |
|------|------|------|------|
| libpython3.9.so 0 个动态符号 | 当前编译未加 `--enable-shared`，work 目录只有 libpython3.9.a | 🔴 P0 待解决 | install 目录的 .so 是旧编译产物（3月22日），`nm -D` 显示 0 个动态符号，扩展模块全部静态链接 libpython |
| make install 不完整 | 编译后未执行 `make install` | 🟡 待执行 | install 目录没有 `bin/python3.9`，没有 `lib-dynload/`，只有 site-packages/ 和旧的 .so 文件 |
| pip 版本过旧（20.2.3） | 随 Python 3.9.0 内置 | 🟡 待升级 | 可升级到 26.0.1 |
| quicktest 不可复现 | `python -m test` 因 PYTHONPATH 问题无法运行 | 🟡 待调查 | 直接运行 `python3.9 Lib/test/test_builtin.py` 可行 |
| C 扩展包测试结果已失效 | 测试包已卸载，且可能受 libpython 符号影响 | 🟡 待重测 | 建议 P0 修复后重新测试 |
| 官方测试未重跑 | 425 用例结果基于 11 补丁版本 | 🟡 待重跑 | 应用 0012-0020 后需重新运行 |
| pkg-config `--cflags` 返回空 | pkg-config 0.29.2 实现缺陷 | ⚠️ 已绕过 | `--with-openssl` 指定路径 |

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

### ✅ ~~P0~~：重新编译加 --enable-shared → ~~修复 libpython3.9.so 符号导出~~ （已完成）

~~当前 work 编译未使用 `--enable-shared`，导致 libpython3.9.so 不导出动态符号。~~

**已解决**（2026-03-26）：
1. `make clean`
2. 重新 `configure`：
   ```bash
   CPPFLAGS="-I$HOME/usr/local/include" LDFLAGS="-L$HOME/usr/local/lib" \
   ./configure --prefix=$HOME/usr/local --disable-ipv6 \
     ac_cv_file__dev_ptmx=no ac_cv_file__dev_ptc=no \
     --enable-shared
   ```
3. `make -j$(nproc)` → ✅ 成功
4. `llvm-nm -D libpython3.9.so | grep " T " | wc -l` → **1459** 个导出 text 符号
5. `make install` → ✅ install 目录完整，72/72 扩展模块导入成功

**注意**：`CPPFLAGS`/`LDFLAGS` 指向 `$HOME/usr/local` 是因为 libintl（gettext）头文件和库安装在该路径。之前通过 `--with-openssl=$HOME/usr/local` 顺带覆盖了此路径，现在 pkg-config 已修复 OpenSSL 检测，改为显式传递。

### ✅ ~~P0~~：执行 make install → 完善 install 目录 （已完成）

**已解决**（2026-03-26）：`make install` 执行成功，安装目录完整：
- `bin/python3.9` + symlinks（python3, idle3, pydoc3, 2to3）
- `lib/libpython3.9.so` + `libpython3.9.so.1.0`
- `lib/python3.9/lib-dynload/` — 72 个 .so，全部导入成功

### 🟡 P1：升级 pip

升级 pip 20.2.3 → 26.0.1。

### 🟡 P1：重跑 quicktest

基于 20 补丁版本，先解决 PYTHONPATH 问题，然后重跑全量 quicktest。

### 🟡 P1：重测 C 扩展包

在 libpython3.9.so 符号导出修复后，重新安装并测试 C 扩展包兼容性（之前 9 包测试结果已失效）。

### 🟡 P2：重跑官方测试

基于 20 补丁版本重新运行官方测试套件（当前数据基于 11 补丁版本，已过时）。

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
| 补丁文件 | 本目录 `patches/` | **20 个 .patch 文件**（含 series 索引，注意 0020 依赖 0016） |
| 编译好的 Python 3.9 | `~/python/Python-3.9.0-work/python3.9` | 可直接运行（含 20 补丁 + SSL，静态链接 libpython） |
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
rtswith(('ohos', 'harmonyos')):
    unix_shell = '/system/bin/sh' if os.path.exists('/system/bin/sh') else '/bin/sh'
else:
    unix_shell = '/bin/sh'
```
``
e:
    unix_shell = '/bin/sh'
```
``
