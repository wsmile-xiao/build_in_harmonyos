# draft-ohos-python-posix-spawn-no-path-search

## 症状

OHOS PC 自带的 python3（`/storage/Users/currentUser/usr/local/bin/python3`，
`ELF 64-bit arm64, dynamic (/lib/ld-musl-aarch64.so.1)`，Python 3.12.9）
用 `subprocess` 执行**裸命令名**必然 `FileNotFoundError`：

```python
import subprocess
subprocess.run(["ls"])            # FileNotFoundError: [Errno 2] ... 'ls'
subprocess.run(["/bin/ls"])       # rc=0 正常
subprocess.run(["conan","--version"])                      # FileNotFoundError
subprocess.run(["/…/usr/local/bin/conan","--version"])     # rc=0（shebang 可执行时）
```

即：**PATH 里明明有该命令，但 `posix_spawn` 不做 PATH 查找**。

## 根因

- CPython 3.12 在 Linux 上默认使用 `os.posix_spawn()` 启动子进程。
- **glibc 的 `posix_spawn()` 会搜索 PATH，musl 的不会**（musl 只让
  `posix_spawnp()` 搜索）。OHOS 是 musl → 裸命令名直接 ENOENT。
- 结论：这不是任务环境「PATH 没配好」，而是 musl 与 glibc 的 ABI 语义差异；
  在 glibc 机器上写的 `subprocess.run(["conan", ...])` 到 OHOS 上必然失败。

## 影响（本任务实测）

- `ohc-run.py result` 的**依赖二次验证硬闸**（`result_report.py`：
  `subprocess.run(["conan","list",f"{pkg}/*","-r=ohpcd","-f=json"])`）
  在 OHOS worker 上永远走到 `except FileNotFoundError` 分支，输出
  `[probe] conan CLI 不可用，跳过 qtwebengine 实测` —— 双层强制中的
  「实测戳穿谎报」那一层**静默失效**（仍有 `[probe]` 行留痕，不会假装实测）。
- 任何在适配脚本里以裸命令名调用 `git`/`patch`/`cmake`/`tar` 的路径同样脆弱。

## 规避 / 建议修复

临时规避（本任务实证可用）：把要调用的命令做成 **绝对路径** 或包一层 shell：

```python
subprocess.run(["/bin/sh","-c","conan list 'qtwebengine/*' -r=ohpcd -f=json"])
# 或 shutil.which("conan") 先解析出绝对路径再传入
```

框架侧建议（任选其一）：
1. `result_report.py` 等所有 `subprocess.run([...])` 调用点统一改为
   `cmd[0] = shutil.which(cmd[0]) or cmd[0]`（或加一个 `run_tool()` 帮助函数）；
2. 或统一 `shell=True` + `shlex.join(cmd)`；
3. 或在 worker 启动时 `export PATH` 之外，另设 `OHC_TOOL_DIR` 并把关键工具软链到
   worker CWD（musl 的 posix_spawn 会在 CWD 找到裸名命令）。

## 验证

```bash
$ python3 -c "import subprocess; subprocess.run(['ls'])"
FileNotFoundError: [Errno 2] No such file or directory: 'ls'
$ python3 -c "import subprocess; print(subprocess.run(['/bin/ls'],capture_output=True).returncode)"
0
$ python3 -c "import os; print(hasattr(os,'posix_spawn'))"
True
$ file /storage/Users/currentUser/usr/local/bin/python3
ELF 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
```

qlog 0.51.1 上报 `dependency_missing` 时，`missing_evidence` 里因此出现
`[probe] conan CLI 不可用，跳过 qtwebengine 实测`（人工实测输出已手工附在
同一字段：`conan list 'qtwebengine/*' -r=ohpcd -> Found 0 pkg/version recipes`）。

## 相关

- 触发实例：qlog/0.51.1 result 上报（2026-09-28）
- 同族：DRAFT-hamlib-4.7.1-langdetect-recursive-makefile-pl-false-perl（同为
  OHOS 环境下的工具误判类问题）
