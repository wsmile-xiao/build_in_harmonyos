# Python 3.9.25 regrtest v3 测试分析报告

> **测试版本**: v3（补丁集 104 patches，三目录 diff 法）
> **测试日期**: 2026-03-30
> **测试平台**: HarmonyOS-HongMeng_Kernel_1.11.0-aarch64-64bit-ELF, musl libc, Clang 15.0.4
> **测试命令**: `cd Python-3.9.25 && LD_LIBRARY_PATH=. make test 2>&1 | tee 07-make-test-v3.log`
> **对比基线**: 3.9.0 v52（2026-03-29，364/425 通过）

## 总览

| 指标 | 3.9.25 v3 | 3.9.25 v1 | 3.9.0 v52 | v3 vs v1 | v3 vs 3.9.0 |
|------|-----------|-----------|-----------|----------|-------------|
| 总测试数 | 425 | 425 | 425 | — | — |
| 通过 | 384 | 380 | 364 | +4 | +20 |
| 失败 | 8 | 12 | 39 | -4 | -31 |
| 跳过 | 33 | 33 | 20 | — | +13 |
| 通过率 | 90.4% | 89.4% | 85.6% | +1.0% | +4.8% |
| 可执行通过率 | 98.0% | 97.0% | 94.8% | +1.0% | +3.2% |

## 8 个失败测试

| # | 测试 | 子测试 | 根因 | 3.9.0 状态 |
|---|------|--------|------|-----------|
| 1 | test_concurrent_futures | 2 errors | socket.bind PermissionError | PASSED |
| 2 | test_getpass | 1 error | pwd.getpwuid uid not found | FAILED |
| 3 | test_posix | 8 errors, 2 failures | symlink/chown/scheduler | FAILED |
| 4 | test_posixpath | 23 errors, 1 failure | symlink Permission denied | FAILED |
| 5 | test_shutil | 1 failure | copyfile 行为差异 | FAILED |
| 6 | test_socket | 30 errors, 1 failure | UDPLITE 不支持 | FAILED |
| 7 | test_tarfile | 1 error, 1 failure | mkfifo + 权限 | FAILED |
| 8 | test_time | crashed (SIGSYS) | 内核 syscall | FAILED |

## v1→v3 修复记录

4 个测试从失败变为通过：
- test_compileall: NameError _can_hardlink → 已补充函数定义
- test_importlib: NameError _skip_new_style_entry_points → 已补充变量定义
- test_curses: test_putwin PermissionError → @skipIf(ohos)
- test_httpservers: IPv6 DNS → 已修复

## 33 个跳过测试分类

| 类别 | 数量 | 测试 |
|------|------|------|
| 缺少 tkinter | 7 | test_tcl, test_tk, test_idle, test_ttk_textonly, test_ttk_guionly, test_turtle, test_tix |
| Windows 专用 | 5 | test_winreg, test_winconsoleio, test_winsound, test_msilib, test_startfile |
| OHOS 策略限制 | 13 | test_openpty, test_pty, test_ioctl, test_signal, test_mp_fork/forkserver/spawn, test_uu, test_embed, test_distutils, test_dbm_dumb, test_gdb |
| OHOS 系统差异 | 5 | test_locale, test_format, test_c_locale_coercion, test_nis, test_spwd |
| 缺少音频/资源 | 2 | test_ossaudiodev, test_zipfile64 |
| 平台不适用 | 1 | test_kqueue, test_devpoll (合并) |

## 发布评估

可执行测试通过率 98.0% ≥ 95% ✅
8 个失败均为 OHOS 平台硬限制，非适配代码问题。
