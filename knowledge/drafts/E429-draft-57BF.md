# DRAFT E429 — lit 用例环境最小化（HOME / PYTHONPATH 不转发）导致上游 lit 套件假失败

- **条目主题**：把上游 lit/llvm-lit（ShTest）套件接进 `test_package` 时，lit 为每个用例重建
  最小环境（仅 `PATH` + `pass_vars` 白名单），`HOME`、`PYTHONPATH` 都会丢；结果是
  riscemu 的 `fibs.asm` 用例假失败、`python3 -m <pkg>` 可能解析到非被测包。
- **状态**：草稿（待知识库主编审核提升编号）
- **关联**：riscemu 2.2.7 适配（`archives/r/riscemu/2.2.7`）、
  `DRAFT-riscemu-2.2.7-*`（同批）、E432（同批：lit 套件接入方式）

## 症状

```text
# 1) 直接跑 lit（test_package/filecheck/ 为上游 test/filecheck 的逐字节副本）
$ lit --timeout=5 -v test_package/filecheck
FAIL: riscemu :: fibs.asm (7 of 11)
...
Failed Tests (1):
  riscemu :: fibs.asm
  Passed: 10
  Failed:  1

# 2) 同一条命令加上 HOME 就过
$ HOME=$HOME lit --timeout=5 -v test_package/filecheck
  Passed: 11

# 3) 手工复现被测命令（不经过 lit）也过
$ python3 -m riscemu -v -o ignore_exit_code,libc test/filecheck/fibs.asm </dev/null
[CPU] Program exited with code 1265227608
```

## 根因

`lit/TestingConfig.py::TestingConfig.fromdefaults()` **从零构造** `environment`：

```python
environment = {'PATH': os.pathsep.join(litConfig.path + [os.environ.get('PATH','')]),
               'LLVM_DISABLE_CRASH_REPORT': '1'}
pass_vars = ['LIBRARY_PATH', 'LD_LIBRARY_PATH', 'SYSTEMROOT', 'TERM', 'CLANG', ...]
for var in pass_vars:
    val = os.environ.get(var, '')
    if val: environment[var] = val
```

`HOME` 与 `PYTHONPATH` 都不在白名单内，因此：

1. **`HOME` 缺失 → `fibs.asm` 假失败**：该用例带 `-o ignore_exit_code,libc`，程序以 `ebreak`
   结束，riscemu 的交互式调试路径 `riscemu/debug.py` 会执行
   `readline.write_history_file(os.path.expanduser("~/.riscemu_history"))`；
   本机 uid 无 passwd home 记录时 `expanduser("~")` 仍是 `~`，写文件抛
   `FileNotFoundError: [Errno 2] No such file or directory`，中断退出码处理，
   于是 `// CHECK: [CPU] Program exited with code 1265227608` 永远不出现。
   这是**测试环境**缺陷，不是模拟器缺陷（手工跑同一命令必过）。
2. **`PYTHONPATH` 缺失 → 被测对象可能不对**：lit 的 `RUN:` 行是 `python3 -m riscemu ...`，
   丢掉 `PYTHONPATH` 后会退回到解释器自身 site-packages 里的 riscemu（若有）或直接
   `ModuleNotFoundError`。conan 配方把包装在包目录里、只通过 `PYTHONPATH` 暴露，
   不转发就等于**没在测本次产物**。
3. **`--timeout=5` 需要 `psutil`**：`lit/LitConfig.py` 在设置 per-test timeout 时
   `import psutil`，缺失直接 fatal：
   `fatal: Setting a timeout per test not supported. Requires the Python psutil module...`

## 修复（riscemu 2.2.7 实测）

`test_package/filecheck/lit.local.cfg`（平台 shim，上游测试文件零改动）：

```python
import os, tempfile
_home = os.environ.get("HOME") or os.path.expanduser("~")
if not os.path.isdir(_home):
    _home = tempfile.mkdtemp(prefix="riscemu-lit-home-")
config.environment["HOME"] = _home
if os.environ.get("PYTHONPATH"):
    config.environment["PYTHONPATH"] = os.environ["PYTHONPATH"]
```

`test_package/conanfile.py::test()` 侧同时准备：

- `pip install 'psutil>=5.9,<6'`（上游 dev 依赖同区间）、`lit>=16,<17`、`filecheck==0.0.23`；
- PATH 最前面放 `dirname(sys.executable)` 与**包自己的 `bin/`**（`p2align.asm` 的
  `RUN: riscemu -o libc ...` 用的是 console script）。

## 验证

```bash
$ lit --timeout=5 -v test_package/filecheck      # 期望 Passed: 11
$ conan create archives/r/riscemu/2.2.7 -pr:h=ci/conan/profiles/ohos-aarch64 \
      -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
HMBS_UPSTREAM_SUITE_LIT={"status":"passed","framework":"lit","discovered":11,"passed":11,...}
HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"pytest+lit","passed":60,...}
```

## 禁止做法

- ❌ 改上游 `.asm/.s` 用例（删 `CHECK` 行 / 加 `XFAIL`）让 lit 变绿 —— 丢掉上游行为基线，
  且测试副本不再逐字节等于上游。
- ❌ 只跑 `pytest` 就宣称「上游测试通过」——lit/filecheck 套件是上游 CI 的另一半。
- ❌ 手工 `export HOME=` 临时绕过而不落进 `lit.local.cfg` —— CI 复现时依旧失败。

## 查重关键词

lit、llvm-lit、ShTest、`TestingConfig.fromdefaults`、`pass_vars`、HOME 不转发、
PYTHONPATH 不转发、`--timeout=5`、psutil、`readline.write_history_file`、
`riscemu/debug.py`、`lit.local.cfg`、平台 shim、filecheck 套件假失败
