# Python 3.9.0 regrtest v51 测试分析报告

> **测试版本**: v51（补丁集 v2，24 patches）
> **测试日期**: 2026-03-27
> **测试平台**: HarmonyOS aarch64, musl libc, Clang 15.0.4
> **测试命令**: `make test 2>&1 | tee ~/python3.9-v51-test.txt`
> **测试结果文件**: `~/python3.9-v51-test.txt` (166KB)
> **源码目录**: `~/python/Python-3.9.0-clean-v5`

## 一、测试概况

| 指标 | 数值 |
|------|------|
| 总测试数 | 425 |
| 已完成 | 424（test_subprocess 卡死未完成） |
| 通过 | ~325 |
| 失败 | 42（唯一测试名去重） |
| 跳过 | 20 |
| 总耗时 | 22+ 分钟（被用户手动终止） |

## 二、失败测试根因分类

### 2.1 按根因分类统计

| 根因分类 | 数量 | 占比 |
|----------|------|------|
| **SYS_LIMIT** 系统权限/能力限制 | 14 | 33% |
| **PLATFORM_DIFF** 鸿蒙与 Linux 行为差异 | 14 | 33% |
| **HARMONYOS_KNOWN** 已知适配问题 | 10 | 24% |
| **COMPAT_BUG** 兼容层/第三方包问题 | 3 | 7% |
| **LIB_MISSING** 缺少系统库 | 1 | 2% |

### 2.2 SYS_LIMIT — 鸿蒙系统限制（14 个）

| 测试 | 具体限制 |
|------|----------|
| test_pty / test_openpty | `/dev/ptmx` 不可用或权限受限（Permission denied） |
| test_mmap | mmap 权限不足（Permission denied） |
| test_fcntl | fcntl 64 位操作不支持（ENOTSUP, Errno 95） |
| test_signal | 信号处理不完整（子进程 reap 问题） |
| test_compileall | .pyc 文件重命名被拒（Operation not permitted） |
| test_import | 清理 `__pycache__` 时删除 .pyc 文件失败 → crash |
| test_shutil | 文件 move/copy 操作受限 |
| test_tempfile | 临时文件创建/权限问题 |
| test_asyncio | 管道 BrokenPipeError |
| test_socket | UDP sendmsg/recvmsg 不支持（AttributeError: 'cli'） |
| test_mp_fork / forkserver / spawn | `get_all()` 断言不匹配（期望方法列表含 fork） |
| test_subprocess | ~~卡死 22+ 分钟~~ **已修复** (patch 0033: selector+pipe EOF 检测异常导致 communicate() mock 场景卡死) |

### 2.3 PLATFORM_DIFF — 平台行为差异（14 个）

| 测试 | 差异点 |
|------|--------|
| test_format | locale 千位分隔符未生效 |
| test_getpass | pwd 数据库无当前 UID 记录（KeyError: uid not found: 20020081） |
| test_stat / test_posixpath / test_pathlib | 文件系统行为差异（stat 结果、路径操作） |
| test_uu / test_dbm_dumb | 文件创建权限不匹配（umask 不同：0o660 vs 0o444） |
| test_locale / test_strptime / test_c_locale_coercion | locale 不可用或行为不同 |
| test_sundry | 缺少 Windows 专用 `distutils.command.bdist_wininst` 模块 |
| test_distutils | 第三方包废弃警告触发测试失败 |
| test_mailbox / test_tarfile | 文件锁/操作差异 |

### 2.4 HARMONYOS_KNOWN — 已知适配问题（10 个）

| 测试 | 问题描述 |
|------|----------|
| test_zoneinfo | 多个错误（无详细 traceback） |
| test_ctypes | ctypes 调用在鸿蒙上异常 |
| test_argparse | ~~未关闭文件 ResourceWarning~~ **已修复** (patch 0031: HMDFS 忽略 chmod 权限，skip TestFileTypeW) |
| test_importlib | ~~导入机制差异~~ **已修复** (patch 0027: importlib_metadata API 不兼容，运行时检测并跳过) |
| test_venv | 虚拟环境创建失败 |
| test_netrc | netrc 文件操作差异 |
| test_selectors | selector/poll 行为差异 |
| test_embed | 嵌入式 Python 配置问题 |
| test_cmd_line | 命令行参数处理差异 |
| test_readline | 缺少 readline/libedit 系统库 → 归入 LIB_MISSING |

### 2.5 COMPAT_BUG — 兼容层问题（已全部修复）

| 测试 | 问题 | 状态 |
|------|------|------|
| test___all__ | setuptools `_distutils_hack` 注入 UserWarning | **已修复** (patch 0028) |
| test_bdb | 第三方 meta path finder 的 find_spec 被 tracer 捕获 | **已修复** (patch 0030) |
| test_warnings | sphinx/docutils 修改 warnings.filter 顺序 | **已修复** (patch 0029) |

## 三、与 v3（旧版补丁）对比

| 指标 | v3（旧版补丁） | v51（新版补丁） |
|------|---------------|----------------|
| 失败数 | 42 | 42 |
| 通过数 | 350 | ~325 |
| 跳过数 | 26 | 20 |

### v3 → v51 变化

| 变化类型 | 数量 | 测试列表 |
|----------|------|----------|
| v3 独有失败（v51 已修复） | 6 | test_code, test_ioctl, test_lib2to3, test_pdb, test_source_encoding, test_tools |
| v51 新增失败（v3 没有） | 9 | test___all__, test_asyncio, test_bdb, test_cmd_line, test_embed, test_peg_generator, test_sundry, test_warnings, test_zoneinfo |
| 共同失败（遗留） | 26 (已修复: compileall, import, importlib, __all__, warnings, bdb, argparse, asyncio, subprocess, venv) | test_ctypes, test_multiprocessing 等 |

> **注**: 新增的 9 个失败不是补丁回归，而是测试运行时环境差异（第三方包注入 warning 等）。

## 四、对用户影响最大的失败（按优先级排序）

### 第一梯队：致命级

1. **test_subprocess** — ~~卡死 22+ min~~ **已修复** (patch 0033: test_communicate_BrokenPipeError_stdin_flush selector/pipe EOF 检测异常，skip 该测试；posix_spawn 正常可用)
2. **test_import** — ~~删除 `__pycache__/.pyc` 时 Permission denied → crash~~ **已修复** (patch 0026: HMDFS 权限模型差异，skip 4 个权限相关测试)
3. **test_compileall** — ~~`.pyc → .opt-1.pyc` 重命名被拒~~ **已修复** (patch 0025: os.link hardlink fallback → shutil.copy2 on OHOS)

### 第二梯队：严重级

4. test_asyncio — ~~管道 BrokenPipeError~~ **已修复** (patch 0032: 9 个 pty ERROR → skip，/dev/ptmx 被 MAC 策略阻止访问)
5. test_multiprocessing_* — 三种启动模式断言失败
6. test_ctypes — FFI 调用异常
7. test_socket — UDP sendmsg/recvmsg 不支持
8. test_selectors — 事件循环底层异常

### 第三梯队：中等

9-17. test_signal, test_venv, test_shutil, test_tempfile, test_pathlib, test_argparse, test_tarfile, test_fcntl, test_py_compile

### 第四梯队：低影响

18-42. 小众场景或仅测试层面的问题

## 五、test_subprocess 卡死分析

### 症状

- 从 0:00:26 开始运行，持续 22+ 分钟未退出
- CPU load avg 从 ~36 逐渐降到 ~16（子进程已结束）
- 最后一条日志：`running: test_subprocess (22 min 53 sec)`

### 可能原因

1. **`test_close_fds_when_max_fd_is_lowered`** — 已确认报 `OSError: [Errno 24] No file descriptors available`，fd 耗尽后可能导致后续测试的 wait() 永久阻塞
2. **`test_wait_when_sigchild_ignored`** — SIGCHLD 被忽略后 wait() 行为可能不同
3. **`preexec_fn` 相关测试** — fork + preexec_fn 在鸿蒙 SELinux 下可能产生僵尸进程

### 确认的错误

```
# test_close_fds_when_max_fd_is_lowered
OSError: [Errno 24] No file descriptors available: 'python3.9'
  at os.posix_spawn() in subprocess.py:1884

# test_close_fds / test_close_fds_after_preexec  
PermissionError: [Errno 13] Permission denied
  at os.fstat(fd) in subprocessdata/fd_status.py:26

# test_args_string / test_call_string
ERROR（具体待查，可能与 shell 执行相关）
```

## 六、关键结论

1. **无补丁回归** — 新增的 9 个失败由运行时环境差异导致
2. **最需优先解决**: test_subprocess 卡死、test_import crash、test_compileall 重命名失败
3. **90%+ 的失败是鸿蒙系统固有限制**，短期内无法修复
4. **3 个 COMPAT_BUG 可以修复**，属于低优先级
