# DRAFT — apertium 3.9.12: 上游 Python 测试套件内嵌裸名 Popen 在 OHOS worker 上 FileNotFoundError

> 触发事件：apertium 3.9.12 HarmonyOS PC 适配（PR #5126，CI 构建 #41152，Worker CI-011）
> 根条目：E405（OHOS 下 python subprocess 裸名命令不搜索 PATH）。本草稿补充其在上游测试源码中的触发面与修复手法。

## 错误特征

```text
ERROR: runTest (adaptdocx.CorrectBoundariesTest.runTest)
  ...
  File ".../python3.12/subprocess.py", line 1804, in _posix_spawn
    self.pid = os.posix_spawn(executable, args, env, **kwargs)
FileNotFoundError: [Errno 2] No such file or directory: 'python3'

ERROR: runTest (adaptdocx.SameTextTest.runTest)
  ...
FileNotFoundError: [Errno 2] No such file or directory: 'cat'
FAILED (errors=2)
```

## 触发条件

- 构建系统：autotools；conanfile.py `build()` 内以 `subprocess.run(["python3", "tests/run_tests.py", ...])` 运行上游 Python unittest 套件
- 上游测试源码（`tests/adaptdocx/__init__.py`）内嵌**裸名**子进程调用：`Popen(["python3", "adaptdocx/extract_docx.py"])` 与 `Popen(["cat", xmlFile])`
- 平台：HarmonyOS PC（OHOS）CI worker，python3 为 hnp 包 python3.12
- 关键差异：**本地开发机的 python3（如 `~/usr/local/bin/python3`）subprocess 走 fork+exec、正常搜 PATH，本地全绿；CI worker 的 hnp python3.12 强制 posix_spawn → PR CI 红**。同一配方，本地过 CI 挂。

## 根因分析

HarmonyOS 的 hnp python3.12 在 `subprocess.py` 中经 `_IS_HARMONYOS` 强制裸名命令也走 `os.posix_spawn()`（非 `posix_spawnp`），不做 PATH 搜索，裸名可执行文件直接抛 `FileNotFoundError`（E405 根因，E055 同族）。

apertium 54 个用例中 52 个经 `../apertium/apertium-*` 相对路径调用构建产物（posix_spawn 对相对/绝对路径可解析）通过；仅 adaptdocx 2 个用例因 `python3`/`cat` 裸名失败——即 52/54 通过、2 个环境性失败，整包被判 FAILED。

## 解决方案

### 推荐方案：env PATH 前置 shim（零补丁）

不修改上游测试源码、不打补丁：运行 `run_tests.py` 时在 env 中把含 `python3` 符号链接的临时 bin 目录前置到 PATH，使测试源码中的裸名调用解析到绝对路径目标：

```python
import os, shutil
py3 = shutil.which("python3") or "/storage/Users/currentUser/usr/local/bin/python3"
shim = os.path.join(build_dir, ".test-shim-bin")
os.makedirs(shim, exist_ok=True)
link = os.path.join(shim, "python3")
if not os.path.exists(link):
    os.symlink(py3, link)
env = {**os.environ, "PATH": shim + os.pathsep + os.environ.get("PATH", "")}
subprocess.run(["python3", "tests/run_tests.py", "-v", "-b=verbose"],
               cwd=build_dir, env=env, ...)
```

- `cat` 在 OHOS worker 属 toybox `/system/bin/cat`，PATH 本就可达，无需注入（日志中 `'cat'` 报错是同一根因的另一表现：posix_spawn 连 PATH 里存在的裸名也不搜）。
- 该手法同样适用于测试源码硬编码其它裸名工具（sed/diff/grep）的场景。

### 禁止做法

- 为 `tests/adaptdocx/__init__.py` 打源码补丁改绝对路径——偏离上游、升级冲突、徒增维护面（对比 R8/补丁规范精神）。
- 直接跳过 adaptdocx 2 个用例——52/54 可全绿时不该放弃这 2 个（R34/R9 测试真实性红线）。

## 验证/命令

```bash
# CI worker 上复现（裸名失败）
python3 -c "import subprocess; subprocess.run(['cat','/dev/null'])"
# FileNotFoundError: [Errno 2] No such file or directory: 'cat'
# 对照：绝对路径成功
python3 -c "import subprocess; subprocess.run(['/system/bin/cat','/dev/null'])"
# 修复后：54/54 全部 OK，conan create 通过
```

## 关键词

Popen, bare-name, python3, cat, FileNotFoundError, Errno 2, posix_spawn, _IS_HARMONYOS, run_tests.py, unittest, tests/adaptdocx, PATH, shutil.which, 绝对路径, wrapper, subprocess, upstream test suite, apertium

---

*来源：PR #5126 构建 #41152 失败日志 + 本地复现差异分析（2026-09-16）*
