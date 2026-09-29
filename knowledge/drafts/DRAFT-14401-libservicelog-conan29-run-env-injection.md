# DRAFT-14401-libservicelog-conan29-run-env-injection

## 摘要

conan 2.29 下，配方 `test()` 里想给测试子进程注入环境变量（DB 路径、QPA 平台、
XDG 目录、TMPDIR、LD_LIBRARY_PATH 等）时，两条老路都断了：

```python
# conan 1.x 写法 A：environment_append —— 2.29 已移除，ImportError
from conan.tools.env import environment_append
# AttributeError: module 'conan.tools.env' has no attribute 'environment_append'

# 写法 B：run(env=list) —— 2.29 只接受列表、且列表不实际注入
self.run("./probe", env=["SERVICELOG_DB=/tmp/x/servicelog.db"])   # 子进程里变量不存在！
```

**正确 API（conan 2.29）**：

```python
from conan.tools.env import Environment

env = Environment()
env.define("SERVICELOG_DB", db)          # 动态值（临时目录）先 mkdtemp 再 define
env.define("SL_TEST_DB", db)
with env.vars(self, scope="run").apply():
    self.run("./probe")                  # 子进程可见，退出上下文自动恢复
```

## 关键判定：run(env=list) 是静默失败

- `run(env=...)` 传字符串会直接报 `env argument to ConanFile.run() should be a list`；
- 改成列表后**不报错，但变量根本没进子进程环境**——只有子进程行为异常才暴露；
- 手动在 shell 里跑同一命令又正常（shell 环境有变量）→ 极易误判为库缺陷，
  反复盲改配方/补丁浪费迭代。

libservicelog/1.1.19 真机实测链：`SERVICELOG_DB` 未注入 → 库按默认
`/var/lib/servicelog/servicelog.db` 打开失败；改为 `env.vars(scope="run").apply()`
后 probe 全过 + 上游 6 场景 SUITE PASS 6/6（conan-verify 迭代 11，Verdict PASS）。

## 最小复现

```python
# 复现：输出 None —— 列表形参不注入
self.run("python3 -c 'import os;print(os.environ.get(\"FOO\"))'", env=["FOO=bar"])

# 验证修复：输出 bar
env = Environment(); env.define("FOO", "bar")
with env.vars(self, scope="run").apply():
    self.run("python3 -c 'import os;print(os.environ.get(\"FOO\"))'")
```

## 推荐解法（rec_approach: use-conan-env-vars-api）

`Environment` 构造变量集 → `env.vars(self, scope="run").apply()` 上下文管理器包裹
`self.run()`：`scope="run"` 限定注入范围（另有 `"build"`），`apply()` 导入
`os.environ`、退出自动恢复、可嵌套。多个变量多 `define` 几行即可，动态值
（临时目录 DB 路径）在 define 前 `mkdtemp`。

## 兜底解法（fallback: inline-shell-prefix）

需兼容更老 conan 2.x 时，命令前内联变量：
`self.run("SERVICELOG_DB={} ./probe".format(db))`。含空格路径需引号、多条命令
不能复用，仅作降级。

## 禁止项

- 禁止写 `run(..., env=[...])`——不报错但不生效，是静默失败；
- 禁止 `from conan.tools.env import environment_append`——2.29 已移除，导入即崩；
- 禁止因测试环境变量缺失而放水跳过断言——应修复注入方式，保留真实覆盖。
