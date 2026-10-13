# tuptime 5.2.5 适配笔记

## 1. 结论速览

| 项 | 值 |
|---|---|
| 上游 | rfmoz/tuptime，tag `5.2.5`，GPL-2.0-or-later |
| 语言 | **Python 3（100%）**，无 C/C++ 源码、无构建系统 |
| 包类型 | `package_type = "application"`（解释型脚本工具，只装不编） |
| 第三方依赖 | **无**（仅 Python 3 标准库） |
| 源码补丁 | 1 个：`patches/0001-src-tuptime.patch`（+4/-1，OHOS 平台识别） |
| 状态 | built（本地 W3 通过，未 commit/push） |

## 2. 环境

- 目标平台：HarmonyOS（`sys.platform == 'ohos'`），aarch64
- 解释器：Python 3.12.9（`/storage/Users/currentUser/usr/local/bin/python3`）
- Conan：2.29.1（OHOS 适配版），profile `ohos-aarch64`
- 工作树：稀疏检出（见 §6 平台坑）

## 3. 关键事实：上游不是 C/C++ 库

`lang-preflight`（R47）实测：

```console
$ python3 scripts/ohc-run.py lang-preflight tuptime 5.2.5 --src <work>/src/..
  ❌ 语言不匹配: task=cpp, detected=python → env_unsupported
{"expected":"cpp","detected_language":"python",
 "language_evidence":{"build_system":"none","manifest":"未发现语言 manifest 文件",
                      "source_stats":"源文件 6 个（bash:6, python:6），主体占比 100%"}}
EXIT=2
```

`src/tuptime` 的 shebang 即 `#!/usr/bin/env python3`；上游 README 自述
“It is written in Python”，`.github/workflows/codeql-analysis.yml` 的
`language: [ 'python' ]`。全树 `find -name '*.c' -o -name '*.cpp' -o -name
'Makefile' -o -name 'CMakeLists.txt'` 无输出。

因此本包按 SKILL `templates/conanfile-headeronly.py.tmpl` **变体 C（解释型
脚本工具打包：只装不编）** 适配，无 `build()`。该路径由用户在本任务中明确
授权（详见 `test_package/MANIFEST.yml` 的 `ohos_notes.language`）。

## 4. 首个真实错误 → 根因 → 修复

### 错误

```console
$ python3 src/tuptime -f /tmp/x/tuptime.db
ERROR:root:System = ohos not supported
EXIT=1
```

### 根因

`src/tuptime:400-409`：

```python
    if sys.platform.startswith('linux'):
        sis = os_linux(sis)
    elif sys.platform.startswith(('freebsd', 'darwin', ...)):
        sis = os_bsd(sis)
    else:
        logging.error('System = %s not supported', sys.platform)
        sys.exit(1)
```

CPython on OpenHarmony 的 `sys.platform` 是 **`'ohos'`**（不是 `'linux'`），
于是落进 `else` 直接退出 —— 一条记录都没写，工具在鸿蒙PC上完全不可用。

### 修复（`patches/0001-src-tuptime.patch`）

```diff
     # Linux
-    if sys.platform.startswith('linux'):
+    # OHOS (HarmonyOS) uses the HongMeng kernel but exposes the Linux
+    # /proc interface and clock_gettime() clocks, so it is handled by
+    # the Linux backend.
+    if sys.platform.startswith(('linux', 'ohos')):
         sis = os_linux(sis)
```

### 为什么是实质适配而非 stub

OHOS 的系统接口与 Linux 完全一致，`os_linux()` 消费的全部接口本机实测可用：

| 接口 | 本机实测 |
|---|---|
| `/proc/uptime` | `3415.15 23628.47` |
| `/proc/stat` | `btime` 行可读 |
| `/proc/sys/kernel/random/boot_id` | `31df778d-ff59-481c-99bd-c1eb317eca43` |
| `clock_gettime(CLOCK_BOOTTIME/MONOTONIC)` | 可用（btime 由二者差值算出） |

修复后 `-v` 日志：`INFO:System = Linux`，`INFO:Sys values = {...}`，完整汇总
报告输出，`EXIT=0`。

### 重新验证

```console
$ python3 src/tuptime -f /tmp/x/tuptime.db
System startups: 	1  since  10/04/26 11:19:21
System shutdowns: 	0 ok  +  0 bad
System life: 	        57m 12s
...
EXIT=0
```

## 5. 第二个观察（不改代码）：默认 DB 路径

`tuptime` 不带参数时用默认 `/var/lib/tuptime/tuptime.db`：

```console
$ tuptime
ERROR:root:Check DB path "/var/lib/tuptime": [Errno 13] Permission denied: '/var'
```

该目录由发行版包管理器预置（`tuptime-install.sh:131-149` 用 root 建 `_tuptime`
用户与目录；`debian/tuptime.install` 装 `src/tuptime → usr/bin`）。鸿蒙PC 的
`/var` 为只读挂载（`mkdir /var/lib` → Permission denied，非 root）且未预置该
目录 —— 这与“任意未预置环境的 Linux 非 root 用户”表现一致，**不是 OHOS 特有
代码缺陷**，故按 R1 最小改动**不修改默认常量**。需要时用 `-f` 或上游自带的
`TUPTIME_DBF` 环境变量（`src/tuptime:456-458`）指定可写路径。

## 6. 平台坑：HMDFS inode 耗尽（本次踩到，非 tuptime 问题）

`git worktree add` 全量检出 `build_in_harmonyos` 会失败：

```console
$ git worktree add ... feat/tuptime-5.2.5 origin/main
error: unable to create file archives/d/dawn/.../test.c
fatal: cannot create directory at 'archives/d/dazz_db'
```

根因：`stat -f /storage/Users/currentUser` →

```
blocks=243207761 free=50967804 avail=50935036 files=48455677 ffree=85133
```

**空闲 inode 仅 85,133**，而仓库受跟踪文件 88,718 个（其中 `archives/` 84,030）。
解决：稀疏检出

```console
$ git worktree add --no-checkout <wt> feat/tuptime-5.2.5 origin/main
$ git -C <wt> sparse-checkout init --cone
$ git -C <wt> sparse-checkout set archives/t scripts ci knowledge templates config docs references tests code probes feedback .gitcode
$ git -C <wt> checkout
```

→ 10,834 个文件，远低于 inode 上限。

## 7. 上游测试（R51 三步法）

### 7.1 清点

| 入口 | 说明 | 用例数 |
|---|---|---|
| `debian/tests/exec-simple` | autopkgtest：`set -e` + `tuptime` | 1 |
| `debian/tests/exec-debug` | autopkgtest：`set -e` + `tuptime -v` | 1 |
| `misc/scripts/tuptime_dbcheck.py` | SQLite 结构/一致性校验器（Test 1…10） | 10 |
| `debian/tests/control` | autopkgtest 声明（`isolation-container`，需 tuptime 已装入 PATH） | — |
| `.github/workflows/codeql-analysis.yml` | CodeQL 安全扫描（language=python），非业务用例 | — |

无 `make check` / ctest / pytest 注册。

### 7.2 实跑（命令 · 原始结果 · 退出码 · 日志）

```console
$ PATH=<install>/bin:$PATH TUPTIME_DBF=<writable>/tuptime.db sh debian/tests/exec-simple
System startups: 	1  since  10/04/26 11:19:21
...
Current uptime: 	59m 31s  since  10/04/26 11:19:21
rc=0

$ PATH=<install>/bin:$PATH TUPTIME_DBF=<writable>/tuptime.db sh debian/tests/exec-debug
（stdout 13 行汇总报告 + stderr 26 行 INFO 日志）
rc=0

$ python3 misc/scripts/tuptime_dbcheck.py -f <writable>/tuptime.db
### Test 1 ### ... ### Test 10 ###
-------------------------
Errors: 0
Fixed: 0
rc=0
```

注：两个 autopkgtest 脚本**原样执行**，仅使用上游自带的 `TUPTIME_DBF`
环境变量把默认 DB 路径指向可写位置（鸿蒙PC `/var` 只读、未预置
`/var/lib/tuptime`）；这是上游文档化的官方覆盖机制，未改写测试脚本。

**统计：上游 12/12 用例通过，0 失败，0 跳过。**

日志：`reports/upstream-tests.log`。

### 7.3 回填

见 `test_package/MANIFEST.yml` 的 `upstream_tests`（含各文件 sha256 与逐项结果）。

## 8. 源码修改

仅 1 个补丁 `patches/0001-src-tuptime.patch`（`src/tuptime`，+4/-1，见 §4）。
无平台宏、无 stub、无新增文件。

## 9. 依赖

**无第三方依赖。** conanfile 不含 `requires` / `tool_requires`。
W0 检查（R36）：`init-build` 输出“检查编译依赖 → ✅ 所有依赖已就绪”；
运行期仅需 Python 3 解释器（标准库）。

## 10. 验证结果

```console
$ conan create . --version=5.2.5 -pr:h=ci/conan/profiles/ohos-aarch64
（见 reports/conan-create.log；rc=0）
$ conan-verify tuptime 5.2.5
（G0-G4 + L2/L4/L5，见 reports/）
```

`test_package` 断言 11 项全通过（含鸿蒙特有 `ohos-platform-backend`）：

```
CASE                      STATUS  DETAIL
version                   PASS    rc=0, Version = 5.2.5
summary-report            PASS    rc=0, 10 report labels present
table-mode                PASS    table header OK
list-mode                 PASS    list layout OK
csv-mode                  PASS    CSV header + row OK
seconds-mode              PASS    epoch timestamp 1791083961 present
kernel-mode               PASS    kernel=HarmonyOS-HongMeng_Kernel_1.12.0-aarch64-64bit
invert-mode               PASS    rc=0, reversed numbering
graceful-shutdown         PASS    graceful shutdown persisted (endst=1), -l still readable
install-layout            PASS    bin/ + share/man/man1/ + licenses/ present
ohos-platform-backend     PASS    sys.platform='ohos' -> Linux backend, rc=0
total=11 pass=11 fail=0 skip=0
```

## 11. 交付物

| 文件 | 说明 |
|---|---|
| `bin/tuptime` | 单文件 Python 3 程序（上游 `src/tuptime` + 补丁 0001） |
| `share/man/man1/tuptime.1` | 上游 man 页 |
| `share/doc/tuptime/tuptime-manual.txt` | 上游参考手册 |
| `licenses/LICENSE` | GPL-2.0-or-later |

## 12. 注意事项

- 上游未提供 `--version` 短开关之外的版本查询；`-v` 的版本横幅在 **stderr**
  （INFO 日志），汇总报告在 stdout。
- `tuptime -g` 的优雅关机只写 `endst=1`，`offbtime`（关机时刻）要等下次启动
  检测到重启才补全；因此未重启前 `-l`/`-t` 看不到 Shutdown 行，验证应查 DB。
- 未安装数据目录供给（本例未做）：systemd/init.d 单元与 `/var/lib/tuptime`
  属发行版集成范畴，本包只交付可执行体与文档。
---

**编译结束**: 2026-10-04 13:35
**最终状态**: built
