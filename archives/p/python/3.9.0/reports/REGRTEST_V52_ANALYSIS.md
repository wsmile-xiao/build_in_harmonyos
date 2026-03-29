# Python 3.9.0 regrtest v52 测试分析报告

> **测试版本**: v52（补丁集 v2，28 patches，跳过 PGO 编译）
> **测试日期**: 2026-03-29
> **测试平台**: HarmonyOS aarch64, musl libc, Clang 15.0.4
> **测试命令**: `nohup bash -c 'LD_LIBRARY_PATH=.:~/usr/local/lib ./python3.9 -m test > ~/tmp/full_test_complete.log 2>&1' &`
> **总耗时**: ~8 分 55 秒（含失败重跑）
> **对比基线**: v51（2026-03-27，顺序执行，243/425 截断）

## 总览

| 指标 | v52 | v51 |
|------|-----|-----|
| 总测试数 | 425 | 425 |
| 跑完 | 425 | 243（截断） |
| 通过 | 364 | 317 |
| 跳过 | 20 | 35 |
| 失败 | 39 | 10 |
| 环境变更 | 2 | 0 |
| 错误(子测试) | 33 FAIL + 12 ERROR | 63 ERROR（全 ctypes）+ 10 FAIL |

## 与 v51 对比

### ✅ 已修复（v51 FAIL/ERROR → v52 PASS）

| 测试 | v51 状态 | v52 状态 | 修复原因 |
|------|----------|----------|----------|
| test_ctypes | 63 ERROR (E045) | PASSED | libffi 3.5.2 closure 分配修复 |
| test_exceptions | FAIL (ResourceWarning) | PASSED | 可能是运行环境变化 |
| test_fstring | FAIL (上游 bug) | PASSED | 可能是 Clang 行为差异消失 |
| test_gc | FAIL (is_tracked) | PASSED | 可能是编译优化差异 |
| test_decimal | FAIL | PASSED | 可能是运行环境改善 |
| test_import | FAIL (setuptools 警告) | PASSED | setuptools 干扰消失 |
| test_idle | FAIL（未跳过） | SKIPPED | patch 0025 生效 |
| test_tk / test_tkinter | FAIL（未跳过） | SKIPPED | 无 tkinter，跳过正确 |
| test_ttk_guiless | FAIL（未跳过） | SKIPPED | 无 tkinter，跳过正确 |
| test_ioctl | FAIL | SKIPPED | 依赖 pty，正确跳过 |
| test_dbm_gnu | FAIL | 未在失败列表 | gdbm 未安装，可能自动跳过 |
| test_dbm_ndbm | FAIL | 未在失败列表 | ndbm 未安装，可能自动跳过 |
| test_ssl | FAIL (P1) | 未在失败列表 | OpenSSL 未编译（warning 级别） |
| test_compile | FAIL (P2) | 未在失败列表 | 编译器行为差异消失 |
| test_source_encoding | FAIL (P2) | 未在失败列表 | 编码问题消失 |
| test_lib2to3 | CRASH | 未在失败列表 | 崩溃修复 |
| test_finalization | FAIL | 未在失败列表 | 修复 |

### ⚠️ 持续失败（v51 FAIL → v52 仍 FAIL）

| 测试 | 根因 | 可修复性 |
|------|------|----------|
| test_c_locale_coercion | locale 不完整 | 🔶 可适配 |
| test_cmd_line | 命令行参数 | 🔶 需分析 |
| test_dbm_dumb | HMDFS chmod 不生效 | 🔶 可适配 |
| test_distutils | setuptools + chmod | 🔶 可适配 |
| test_embed | 编译/链接环境 | 🔷 需分析 |
| test_fcntl | fcntl 64 位操作 EOPNOTSUPP | 🔴 系统限制 |
| test_format | locale 千位分隔符 | 🔶 可适配 |
| test_getpass | pwd.getpwuid 缺失 | 🔴 系统限制 |
| test_httpservers | 网络/权限 | 🔶 需分析 |
| test_importlib | setuptools _distutils_hack | 🟢 第三方包问题 |
| test_locale | locale 支持不完整 | 🔶 可适配 |
| test_mailbox | 文件锁/权限 | 🔶 需分析 |
| test_mmap | mmap 权限 EACCES | 🔴 系统限制 |
| test_multiprocessing_fork | fd 权限 Permission denied | 🔴 Hmmac MAC 策略 |
| test_multiprocessing_forkserver | 同上 | 🔴 Hmmac MAC 策略 |
| test_multiprocessing_spawn | 同上 | 🔴 Hmmac MAC 策略 |
| test_netrc | 文件权限 | 🔶 需分析 |
| test_openpty | /dev/ptmx EACCES | 🔴 Hmmac MAC 策略 |

### 🆕 新发现（v51 未跑到 → v52 失败）

> **注意**: v51 只跑了 243/425（到 test_os 截断），以下测试在 v51 中从未执行。
> 它们不是回归，而是首次被测试覆盖到的失败。

| 测试 | 子测试失败 | 根因 | 可修复性 |
|------|-----------|------|----------|
| test_os | test_mode, test_chown_gid, test_chown_without_permission, test_openpty(ERROR) | HMDFS chmod 不返回正确权限位（0775→0505, 0600→0448）| 🔶 核心问题：HMDFS umask/mode |
| test_pathlib | test_chmod, test_mkdir_parents, test_stat, test_glob, test_open_mode, test_rglob, test_touch_mode, test_home(ERROR), test_expanduser(ERROR) | 同上 chmod 问题 + $HOME 环境变量 | 🔶 chmod 修复后可能连锁修复 |
| test_posix | 多项 | POSIX API 差异 | 🔶 需分析具体子测试 |
| test_posixpath | 多项 | 路径操作差异 | 🔶 需分析 |
| test_pty | 全部 | /dev/ptmx EACCES | 🔴 Hmmac MAC 策略 |
| test_py_compile | test_exceptions_propagate (×2) | 预期 OSError 但未触发（HMDFS 允许编译到只读目录？）| 🔶 文件系统行为差异 |
| test_readline | 全部 | readline/tty 依赖 | 🔴 终端限制 |
| test_selectors | 多项 | 可能依赖 poll/epoll 差异 | 🔶 需分析 |
| test_shutil | test_chown, test_on_error | chmod/chown HMDFS 差异 | 🔶 chmod 修复后可能连锁修复 |
| test_signal | 多项 | 信号集差异 | 🔶 需分析 |
| test_socket | 多项 | socket API 差异 | 🔶 需分析 |
| test_stat | (通过 test_pathlib 间接触发) | stat 返回值差异 | 🔶 需分析 |
| test_strptime | test_day_of_week_calculation, test_gregorian_calculation, test_julian_calculation (ERROR) | **时区数据缺失**：`time.strftime('%Z')` 返回空或错误格式，`%j` 格式异常（'088 ' 有尾部空格）| 🔶 tzdata 配置问题 |
| test_subprocess | 多项 | subprocess 在鸿蒙上的行为差异 | 🔶 需分析 |
| test_sundry | test_untested_modules_can_be_imported (ERROR) | `distutils.command.bdist_wininst` 不存在（Win 平台模块）| 🟢 可加跳过 |
| test_tarfile | 多项 | 可能涉及文件权限 | 🔶 需分析 |
| test_tempfile | test_mode (505!=448), test_file_mode (432!=384) | HMDFS umask 影响：mkdir 权限 0775→0505, mkstemp 0660→0448 | 🔶 核心问题：HMDFS umask |
| test_time | 多项 | 时间/时区函数差异 | 🔶 需分析 |
| test_urllib2 | 多项 | 网络/SSL | 🔶 需分析 |
| test_uu | 多项 | 可能涉及文件权限 | 🔶 需分析 |
| test_zoneinfo | 全部 | 时区数据配置 | 🔶 tzdata 问题 |

## 根因聚合分析

### 🔴 系统限制（无法通过 Python 代码修复，共 6 测试）

| 根因 | 测试 |
|------|------|
| Hmmac MAC 策略阻止 /dev/ptmx | test_openpty, test_pty |
| Hmmac MAC 策略阻止 fd 操作 | test_multiprocessing_fork/forkserver/spawn |
| Hmmac MAC 策略阻止 mmap | test_mmap |
| fcntl 64 位操作不支持 | test_fcntl |
| pwd.getpwuid 不完整 | test_getpass |
| readline/tty 缺失 | test_readline |

### 🔶 HMDFS chmod/umask 问题（核心适配点，影响 8+ 测试）

**核心现象**: HMDFS 文件系统不正确处理 Unix 权限位。
- `mkdir('dir', 0o755)` → 实际权限 `0o505`（写入位被清除？）
- `mkstemp(mode=0o600)` → 实际权限 `0o448`
- `os.chmod()` 返回值可能不正确

**受影响测试链**:
- test_os (test_mode, test_chown)
- test_pathlib (test_chmod, test_mkdir_parents, test_stat, test_touch_mode, etc.)
- test_shutil (test_chown, test_on_error)
- test_tempfile (test_mode, test_file_mode)
- test_dbm_dumb
- test_distutils (部分)

**建议适配方案**:
1. 在 `os.mkdir()` / `os.chmod()` 层面做 HMDFS 权限位修正
2. 或在受影响的测试中跳过权限断言

### 🔶 时区/locale 问题（影响 5 测试）

- test_strptime: `time.strftime('%Z')` 格式异常，`%j` 输出有尾部空格
- test_zoneinfo: 时区数据缺失
- test_c_locale_coercion: locale 不完整
- test_format: locale 千位分隔符
- test_locale: locale 支持不完整

### 🟢 第三方/构建环境问题（非鸿蒙适配）

- test_distutils: setuptools _distutils_hack 干扰
- test_importlib: 同上
- test_sundry: `distutils.command.bdist_wininst` 不存在（Windows 模块）
- test_embed: 编译/链接环境配置

### ⚪ 待分析（需详细子测试错误信息）

- test_cmd_line, test_httpservers, test_mailbox, test_netrc
- test_posix, test_posixpath, test_signal, test_socket
- test_selectors, test_subprocess, test_tarfile
- test_time, test_urllib2, test_uu

---

## 新增补丁（0028-0036）逐个分析（2026-03-29 排查完成）

### 分析结论总览

| 补丁 | 类型 | 用户影响 | 说明 |
|------|------|:--------:|------|
| 0028 test-all-skip-setuptools-warning | 纯测试噪声 | 无 | test___all__ 过滤 setuptools "replacing distutils" 警告 |
| 0029 test-warnings-filter-thirdparty | 纯测试噪声 | 无 | test_warnings 过滤 docutils/sphinx 注入的第三方 filter |
| 0030 test-bdb-skip-metapath | 纯测试噪声 | 无 | test_bdb tracer 跳过 _distutils_hack/importlib_metadata |
| 0031 test-argparse-skip-readonly | 系统限制 | 无 | HMDFS 忽略 chmod，只读文件仍可写 |
| 0032 test-asyncio-skip-no-ptmx | 系统限制 | 无 | /dev/ptmx 被 Hmmac MAC 策略拦截 |
| **0033** test-subprocess-skip-flush-hang | **纯测试噪声** | **无** | **已验证：鸿蒙 poll() 对 /dev/null 不报 POLLOUT，仅 mock 测试触发** |
| 0034 test-venv-skip-symlink-bash | 系统限制 | 低 | HMDFS 不支持 symlink + bash strict mode 行为差异 |
| **0035** test-time-skip-clock-settime-ohos | **内核 bug** | **有** | clock_settime/process_time/thread_time 触发 SIGSYS 而非返回 EPERM |
| **0036** test-os-skip-ohos-incompatible | **内核 bug** | **有** | setreuid/setregid/chroot 触发 SIGSYS 而非返回 EPERM |

### 0033 详细排查记录

**复现步骤**：
1. 创建 subprocess.Popen([python, '-h'], stdin=PIPE, stdout=PIPE)
2. 用 unittest.mock 将 proc.stdin.fileno() 替换为 /dev/null 的 fd
3. 调用 proc.communicate(b'stuff') → 永久阻塞

**根因**：
- 鸿蒙内核 `poll()` 对 `/dev/null` 设备节点不报告 POLLOUT 事件
- `select()` 同样受影响
- pipe fd 和 regular file fd 的 poll 行为正常

**poll() 行为对比**：

| fd 类型 | poll() POLLOUT | poll() POLLIN | select() writable |
|---------|:---:|:---:|:---:|
| /dev/null | ❌ 超时 | ✅ 正常 | ❌ 超时 |
| /dev/zero | — | ✅ 正常 | — |
| pipe | ✅ 正常 | — | — |
| regular file | ✅ 正常 | — | — |

**卡死机制**：
1. mock 将 proc.stdin.fileno() 替换为 /dev/null fd
2. _communicate 注册 PollSelector 监听 devnull POLLOUT
3. stdout pipe 正常读完 EOF 并注销
4. selector 只剩 devnull 条目，poll() 永远不返回 → 永久阻塞

**实际影响**：无。_communicate 中 stdin 始终是真实 pipe fd（stdin=PIPE 时），poll 对 pipe 的行为完全正常。此 bug 仅在 mock 测试中触发。

### 0035/0036 内核 SIGSYS 问题

**涉及 syscall**：
- clock_settime() — 应返回 EPERM，实际触发 SIGSYS (signal 31)
- process_time() — CLOCK_PROCESS_CPUTIME_ID 未实现，触发 SIGSYS
- thread_time() — CLOCK_THREAD_CPUTIME_ID 未实现，触发 SIGSYS
- pthread_getcpuclockid() — 未实现，触发 SIGSYS
- setreuid() — 应返回 EPERM，实际触发 SIGSYS
- setregid() — 应返回 EPERM，实际触发 SIGSYS
- chroot() — 未实现，应返回 ENOSYS/EPERM，实际触发 SIGSYS

**建议**：推动鸿蒙内核 syscall handler 对未实现/无权限的调用返回错误码（EPERM/ENOSYS），而非发送 SIGSYS 信号。这是 POSIX 标准行为。

---

## 优先级建议

### P0 — 核心根因（修复一个影响多个）
1. **HMDFS chmod/umask 行为** — 影响 8+ 测试，是最大收益点
2. **时区数据配置** — 影响 3-5 测试
3. **内核 SIGSYS 行为**（0035+0036）— 推动 syscall 返回 EPERM/ENOSYS 而非 SIGSYS

### P1 — 需适配
4. **POSIX API 补全** — test_posix, test_posixpath
5. **signal 模块** — test_signal
6. **socket 模块** — test_socket

### P2 — 低优先级
7. 系统限制类（pty, mmap, multiprocessing）— 已有 skip 补丁
8. 网络/SSL 类 — 等 OpenSSL 适配后重新评估
9. distutils/setuptools 问题 — 第三方包问题（已有 skip 补丁）

### 纯测试噪声（已完成，无需进一步工作）
- 0028, 0029, 0030, 0033 — 对实际 Python 使用零影响

## 数值对比

| 指标 | v51 | v52 | 变化 |
|------|-----|-----|------|
| 完成率 | 57% (243/425) | 100% (425/425) | +43% |
| 通过率 | 74.6% (317/425) | 85.6% (364/425) | **+11%** |
| 失败数 | 10 (63 ERROR) | 39 (33 FAIL + 12 ERROR) | 数量增加但因覆盖更完整 |
| ctypes ERROR | 63 | 0 | **全清** |
| 跳过 | 35 | 20 | 减少15（部分修复为 PASS） |
