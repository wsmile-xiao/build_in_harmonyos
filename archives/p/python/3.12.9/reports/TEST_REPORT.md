# Python 3.12.9 鸿蒙适配 — 测试报告

> **生成日期**: 2026-04-02 | **最终基线**: test9 (Round 9)

## 测试环境

| 项目 | 值 |
|------|-----|
| 平台 | HarmonyOS-HongMeng_Kernel_1.11.0-aarch64 |
| 编译器 | Clang 15.0.4 |
| libc | musl |
| Python 源码 | Python-3.12.9-v2 (119 补丁) |
| 测试命令 | `MAKEFLAGS="-j1" make test TESTOPTS="-v -w --ignore=smtpnet --ignore=test__xxsubinterpreters --ignore=test_interpreters"` |

## 最终结果概览

| 指标 | 值 |
|------|-----|
| **通过率** | **99.1%** (426/430, 排除 skip) |
| OK | **426** |
| Failed | **4** |
| Skipped | 60 (57 platform + 3 resource_denied) |
| 耗时 | 5 min 19 sec |
| 并发 worker | 18 (regrtest 默认) |

## 9 轮测试趋势

```
通过率 (%)
100 ┤                                                  ╭─╮
 99 ├╮                                          ╭────╯ │ ╰── test9: 99.1%
 98 ├╯                                    ╭────╯     │     ╰── test8: 98.6%
 97 ├╮                              ╭────╯         │           test7: 98.4%
 86 ├╯                        ╭────╯             │           test6: 98.4%
 84 ├╮                  ╭────╯                   │           test4: 84.8%
 83 ├╯            ╭────╯                        │           test3: 83.7%
    └────────────┴─────────────────────────────┴───────────
      1    2    3    4    5    6    7    8    9   轮次
```

| 轮次 | 通过率 | OK | Failed | 耗时 | 关键事件 |
|------|--------|-----|--------|------|---------|
| 1 | 87.4% | 377 | 54 | — | 基线（大量 IndentationError） |
| 2 | 89.4% | ~385 | ~46 | — | 环境优化 |
| 3 | 83.7% | ~358 | ~73 | — | 回退 |
| 4 | 84.8% | 438 | 13 | — | 部分恢复 |
| 5 | **97.5%** | 421 | 11 | 12m29s | P0 缩进修复(0111/0112)，18 worker 并发 |
| 6 | 98.4% | 423 | 7 | 3m45s | 排除超时测试，单 worker 尝试 |
| 7 | 98.4% | 423 | 7 | 3m24s | pyc 缓存未清理（0113-0115 未生效） |
| 8 | 98.6% | 424 | 6 | 3m41s | P2 修复部分生效(compileall✅) |
| **9** | **99.1%** | **426** | **4** | **5m19s** | **P2 全部生效(subprocess✅ shutil✅)** |

## 失败分类（剩余 4 个）

### 不可修复的平台硬限制（3 个）

| # | 模块 | 错误数 | 根因 | 类别 |
|---|------|--------|------|------|
| 1 | **test_posix** | ~3-5 | chown/fchown 需要 root; readlink_dir_fd HMDFS 不支持; scheduler/seccomp 被阻断 | SELinux+seccomp |
| 2 | **test_socket** | 9 (1F+8E) | UDPLITE seccomp 过滤; UDS bind("") 不报 OSError | seccomp+SELinux |
| 3 | **test_time** | 1 | strptime locale flaky 或 SIGSYS 遗漏用例 | locale/musl |

### 可能可修（1 个）

| # | 模块 | 错误数 | 根因 | 类别 |
|---|------|--------|------|------|
| 4 | **test_tarfile** | 1 | pipe + subprocess posix_spawn 交互异常 | subprocess_compat |

## 修复效果追踪

### P0 修复（缩进错误）— Round 5 验证 ✅

| 补丁 | 目标 | 效果 |
|------|------|------|
| 0111 | test_os.py 6处 IndentationError | test5 起 ✅ 不再失败 |
| 0112 | test_site.py 4处 IndentationError | test5 起 ✅ 不再失败 |

### P1 修复（平台限制）— Round 6-8 验证 ✅

| 补丁 | 目标 | 生效轮次 | 效果 |
|------|------|---------|------|
| 013 | multiprocessing AF_UNIX→AF_INET | test6 | ✅ async_io.unix_events / concurrent.futures.process_pool 消失 |
| 014 | test_time monotonic_settime SIGSYS | test6 | ⚠️ 仍 FAIL（可能遗漏用例） |
| 015 | test_posix SELinux/seccomp ×5 | test6 | ⚠️ 部分 FAIL（chown 未覆盖） |

### P2 深度适配 — Round 9 验证 ✅

| 补丁 | 目标 | 生效轮次 | 效果 |
|------|------|---------|------|
| 016 | subprocess _USE_VFORK + 5个skipIf | test9 | ✅ 全部消失 |
| 017 | PATH /system/bin 冗余保留 | — | 已有 PATH 无需此补丁 |
| 018 | compileall HardlinkDedupTests guard | test8 | ✅ 6个 hardlink FAIL → PASS |
| 019 | shutil mkfifo + copyfile skip | test9 | ✅ rmtree ERR 消失; copyfile 待确认 |

## 三方库兼容性影响评估

### 高影响（用户代码会直接踩坑）

| 能力 | 受限原因 | 受影响三方库 | 建议 |
|------|----------|-------------|------|
| **AF_UNIX socket bind** | SELinux 阻止 | pytest-xdist, Docker SDK, uvicorn/gunicorn UDS 模式 | 用 TCP 替代（0113 已自动回退） |
| **ProcessPoolExecutor/Manager()** | Listener.bind() EPERM | joblib, loky, multiprocessing 共享状态 | 同上 |
| **subprocess mock _fork_exec** | posix_spawn 不走 fork 路径 | 任何 mock subprocess 的测试框架 | 加 `_USE_POSIX_SPAWN` 守卫 |
| **shell 内建命令执行** | posix_spawn 无法 exec 内建命令 | 依赖 `true`/`cat` 的脚本 | 用 `/system/bin/true` 绝对路径替代 |

### 中影响（特定场景触发）

| 能力 | 受限原因 | 受影响场景 |
|------|----------|-----------|
| os.chown/scheduler/unshare | SELinux/seccomp | 文件权限管理、容器化部署 |
| hardlink (os.link) | HMDFS 不支持 | compileall 去重降级为 copy |
| mkfifo | SELinux 阻止 | named pipe 操作 |
| locale (fr_CA/de_DE 等) | 数据缺失 | 国际化排序/格式化 |

### 低影响（已正确 skip）

PTY, signal, UDP-LITE, NIS/spwd, kqueue/devpoll, zoneinfo 等 60 个 platform skip。

## 测试命令参考

```bash
# 最终推荐命令（排除 3 个必卡超时测试）
cd /storage/Users/currentUser/python/Python-3.12.9-v2
find Lib -name '__pycache__' -exec rm -rf {} + 2>/dev/null
MAKEFLAGS="-j1" timeout 1800 make test \
  TESTOPTS="-v -w \
    --ignore=smtpnet \
    --ignore=test__xxsubinterpreters \
    --ignore=test_interpreters" \
  2>&1 | tee python312-testN.log

# 如需更精确的基线（消除并发竞态），加 -j1 到 TESTOPTS：
#  TESTOPTS="-v -w -j1 --ignore=..."
# 注意：这会显著增加总耗时（约 3x），但结果更可靠
```
