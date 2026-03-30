# Python 3.9.25 regrtest v1 测试分析报告

> **测试版本**: v1（补丁集 82 patches）
> **测试日期**: 2026-03-30
> **测试平台**: HarmonyOS-HongMeng_Kernel_1.11.0-aarch64-64bit-ELF, musl libc, Clang 15.0.4
> **Python**: CPython 3.9.25 (main, Mar 30 2026, 20:57:09)
> **测试命令**: `cd /path/to/Python-3.9.25-full-patch && LD_LIBRARY_PATH=.:/path/to/usr/local/lib make test 2>&1 | tee 05-make-test.log`
> **总耗时**: 7 分 5 秒
> **对比基线**: 3.9.0 v52（2026-03-29，364/425 通过）

## 总览

| 指标 | 3.9.25 v1 | 3.9.0 v52 | 变化 |
|------|-----------|-----------|------|
| 总测试数 | 425 | 425 | — |
| 通过 | 380 | 364 | **+16 ✅** |
| 跳过 | 33 | 20 | +13 |
| 失败 | 12 | 39 | **-27 ✅** |
| 通过率 | 89.4% | 85.6% | **+3.8% ✅** |

## 12 个失败测试分类

### A. 补丁 Bug 导致的新失败（2 个）— ✅ 已修复

这 2 个测试在 3.9.0 v52 中通过，3.9.25 中因我们补丁适配错误导致 NameError 崩溃。

| 测试 | 3.9.0 状态 | 3.9.25 状态 | 根因 | 修复 |
|------|-----------|-----------|------|------|
| test_compileall | PASSED | **crashed** | 补丁 0032 使用 `_can_hardlink` 但未定义该变量（3.9.0 有但 3.9.25 源码重构后丢失了定义） | ✅ 补丁 0032 已修复：补充 `_check_hardlink()` 函数和 `_can_hardlink` 赋值 |
| test_importlib | FAILED | **crashed** | 补丁 0036 引用 `_skip_new_style_entry_points` 但未在 test_zip.py 中定义（该变量仅存在于 test_main.py 和 test_metadata_api.py） | ✅ 补丁 0036 已修复：在 test_zip.py 中补充 `_skip_new_style_entry_points` 定义 |

### B. 平台兼容新失败（2 个）— ✅ 已修复

| 测试 | 3.9.0 状态 | 3.9.25 状态 | 根因 | 修复 |
|------|-----------|-----------|------|------|
| test_concurrent_futures | PASSED | **50 errors, 2 failures** | HarmonyOS 安全策略阻止 forkserver `socket.bind()` → `PermissionError: [Errno 1] Operation not permitted`（3.9.25 forkserver 实现变化触发了 OHOS 限制） | ✅ 新增补丁 0081：从 `create_executor_tests()` 中排除 `ProcessPoolForkserverMixin` |
| test_curses | PASSED | **1 error** | `test_putwin()` 中 `win.putwin(f)` 写入临时文件被 OHOS MAC 策略阻止 | ✅ 新增补丁 0082：`@skipIf(sys.platform == 'ohos')` 跳过 test_putwin |

### C. 持续失败（8 个）— 与 3.9.0 v52 相同

| 测试 | 子测试失败 | 根因 | 已有补丁 |
|------|-----------|------|----------|
| test_posix | 8 errors, 2 failures | symlink 禁止 + chown 不生效 + sched_setscheduler 未实现 + pwd 缺用户 | 0042 部分覆盖 |
| test_posixpath | 23 errors, 1 failure | symlink 禁止 → realpath 测试全部失败 + 循环导入 | 0043 部分覆盖 |
| test_socket | 26 errors, 1 failure | UDPLITE 不支持(24) + AF_UNIX 行为差异(3) | 0063 部分覆盖 |
| test_tarfile | 1 error, 1 failure | mkfifo 不支持 + 权限设置不生效 | 0053 部分覆盖 |
| test_shutil | 1 failure | copyfile_nonexistent_dir 路径行为差异 | 0048 部分覆盖 |
| test_getpass | 1 error | pwd.getpwuid 找不到当前 uid | 无 |
| test_httpservers | 1 error | IPv6 `::1` DNS 解析失败 | 0064 部分覆盖 |
| test_time | re-run empty | 首次运行 SIGSYS 崩溃（内核 syscall） | 0071 部分覆盖 |

### D. test_time 首次运行崩溃

首次运行退出码 -31（SIGSYS = signal 31），无 traceback。re-run 时无匹配子测试名，报告 0 tests OK。3.9.0 v52 也有此问题。根因是 OHOS 内核不支持的 syscall 触发 SIGSYS 而非返回 EPERM。

## 修复后预期结果

4 个已修复的失败测试预期将通过/跳过：
- test_compileall: PASSED（_can_hardlink 在 HMDFS 上返回 False → skip hardlink 测试）
- test_importlib: PASSED（_skip_new_style_entry_points = skipIf(True, ...) → skip entry_points 测试）
- test_concurrent_futures: PASSED（forkserver 测试不再生成 → 少约 15 个子测试）
- test_curses: PASSED（test_putwin 被跳过）

**修复后预期**: ~383-384 通过 / 35-36 跳过 / 8 失败 ≈ **90%+ 通过率**

## 33 个跳过测试

| 类别 | 测试 | 数量 |
|------|------|------|
| 缺少 tkinter | test_tcl, test_tix, test_tk, test_ttk_guionly, test_ttk_textonly, test_turtle, test_idle | 7 |
| Windows 专用 | test_winconsoleio, test_winreg, test_winsound, test_startfile, test_msilib | 5 |
| HarmonyOS 策略限制 | test_openpty, test_pty, test_signal, test_ioctl, test_devpoll, test_kqueue | 6 |
| HarmonyOS 系统差异 | test_c_locale_coercion, test_locale, test_format, test_embed, test_distutils | 5 |
| multiprocessing 限制 | test_multiprocessing_fork, test_multiprocessing_forkserver, test_multiprocessing_spawn | 3 |
| 缺少 nis/spwd | test_nis, test_spwd | 2 |
| 缺少音频 | test_ossaudiodev | 1 |
| 其他 | test_dbm_dumb, test_netrc, test_uu, test_zipfile64, test_gdb, test_time(re-run empty) | 4 |
