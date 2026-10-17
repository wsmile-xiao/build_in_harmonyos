# DRAFT-pyjson5-0.15.0-unittest-pythonpath-recovery

## 纯 Python unittest 上游测试的运行时环境恢复（PYTHONPATH 注入）

### 问题

纯 Python unittest 套件中，部分用例以 out-of-proc 子进程执行被测包（如
`[sys.executable, '-m', 'json5']`），子进程 cwd 是新建临时目录（不在 sys.path）。
上游 CI 依赖预安装环境（uv）使 `python -m <pkg>` 在任何 cwd 可用；未安装环境下
子进程找不到包 → ModuleNotFoundError，整组用例失败（pyjson5 tool_test 15/15 失败，
lib/host 60/60 通过——两类用例同包但只有子进程形态受影响）。

### 根因

子进程 cwd 为临时目录且包未安装入解释器环境；上游 `python run tests` 依赖 uv 预装
（venv 已含该包）。

### 处理方法

1. 根因验证：临时 cwd 下 `python3 -m json5 --help` exit=1（ModuleNotFoundError）；
   注入 `PYTHONPATH=<源码根>` 后 exit=0（子进程继承环境变量）。
2. 恢复重跑：`PYTHONPATH=<源码根> TMPDIR=<可写目录> python3 -m unittest discover -p '*_test.py' -v`
   （TMPDIR 同时规避 /tmp erofs，E002）。
3. 全量通过率以重跑后真实结果计（75/75 = 100%）；首轮失败日志与恢复证据如实留档。

### 落地

pyjson5 0.15.0：重跑后 doctest exit 0 + unittest `Ran 75 tests ... OK`（日志 sha256
f11778f5…fa153fcd；首轮失败日志 84f188e4…a09245 留档）。未修改任何上游测试。

### 适用范围

所有以 out-of-proc 子进程执行被测 python 包的上游套件；验证"源码头"注入源码根，
验证"已安装制品"注入 site-packages，两者不可混用；含 C 扩展或私有模块依赖的包
需先安装（pip/setup.py）再注入已安装路径。