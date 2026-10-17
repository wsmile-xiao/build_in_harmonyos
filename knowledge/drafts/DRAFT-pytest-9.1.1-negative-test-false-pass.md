# draft-pytest-9.1.1-negative-test-false-pass

## 症状

CI 的破坏性负向测试（L1e / R34）把 `package_folder` 下的产物目录移走后重跑 `conan test`，
测试**依然通过**，于是被判定为"假测试"：

```
[step] L1e: Destructive negative test (R34)...
[sabotage] lib/ moved away
[fail] L1e: test passed WITHOUT package artifacts — fake test detected (R34)
test does not depend on iniconfig — must call its API or execute its binary
L1_RESULT=fail: negative test: test does not depend on package
```

矛盾之处在于：**包本身是完好的**，产物能 import、能跑、消费者侧 35 项断言全过。失败的
不是包，而是"测试是否真的绑在产物上"这件事——测试通过了一条与被测包无关的路径拿到了结果。

## 根因

`test_package` 在 `env="conanrun"` 下依赖 conanrun 注入的 `PYTHONPATH` 指向包的
site-packages。但解释器的模块搜索顺序在 PYTHONPATH 之后，仍会回落到 **user site**
（`~/.local/lib/pythonX.Y/site-packages`）。

当开发机或 CI 恰好在 user site 装过同名分发包时（对 pytest / iniconfig 这类**测试基础设施
包几乎必然成立**——它们本来就是被 `pip install` 装到 user site 的东西），产物被移走后：

- 负向跑（CI 移走 `lib/`）：`import iniconfig` 落到 `~/.local/.../iniconfig` → 测试通过 → 判假测试；
- 正向跑：同样落到 user site → 断言看似全过，其实验的不是本包。

三向探针（本机实测）：

| 条件 | 结果 |
|---|---|
| `PYTHONPATH=<不存在的目录>` | `import iniconfig` **成功**，解析到 `~/.local/lib/python3.12/site-packages/iniconfig/__init__.py` |
| 同上 + `-s`（屏蔽 user site） | `ModuleNotFoundError: No module named 'iniconfig'` ✅ 正是负向测试需要的 |
| 默认路径下 `importlib.util.find_spec` | 六个模块（iniconfig/pytest/pluggy/packaging/pygments/py）**全部**从 user site 解析 |

原实现的缺口在于：它只记录并断言了 `realpath(__file__)` 的**目录名**是 `iniconfig`。

```python
pkg_root = os.path.realpath(os.path.dirname(iniconfig.__file__))
check(os.path.basename(pkg_root) == "iniconfig", ...)   # ← 任何来源都满足
```

`realpath` 只把路径规范化，**不构成来源校验**：user site 的副本同样叫 `iniconfig`，
同样有 `__init__.py`，于是断言全部通过。

## 修复

把"模块必须来自本包"变成显式、可被负向测试证伪的性质：

**① conanfile 传入 package_folder**

```python
pkg = self.dependencies["iniconfig"].package_folder
self.run(f'{py} "{script}" "{pkg}"', env="conanrun")
```

**② 脚本先做来源校验，再跑其余断言**

```python
package_folder = os.path.realpath(sys.argv[1])
expected_site = os.path.join(package_folder, "lib", "python3.12", "site-packages")

# 先断言期望路径存在（这样 CI 移走 lib/ 后会在此处失败，而不是被 user site 救活）
check(os.path.isfile(os.path.join(expected_site, "iniconfig", "__init__.py")),
      f"packaged module missing: {expected_site}/iniconfig/__init__.py")

# 再断言实际导入的模块确实落在该路径之下
check(pkg_root.startswith(expected_site + os.sep),
      f"imported iniconfig is not the packaged tree: {pkg_root}")
```

**③ 子进程探针设 `PYTHONNOUSERSITE=1`**

```python
env={**os.environ, "PYTHONNOUSERSITE": "1"}
```

让"新解释器能导入"只可能来自打包的 PYTHONPATH，而不是恰好存在的 user site 副本。

三条合起来，负向测试的语义就真正成立：产物被移走 → 期望路径不存在 → 断言失败 → `conan test`
非零退出。

## 验证

**正向**：`INICONFIG_CONSUMER=PASS assertions=35`（含新增来源校验 2 项）、
`PYTEST_CONSUMER=PASS assertions=41`。

**负向（本机复演 CI 的破坏动作）**：

```
$ mv <package_folder>/lib /tmp/backup
$ conan test test_package pytest/9.1.1 -pr ohos17 --build=missing
AssertionError: packaged module missing: <package_folder>/lib/python3.12/site-packages/pytest/__init__.py
ERROR: pytest/9.1.1 (test package): Error in test() method, line 31
    self.run(f'{py} "{script}" "{pkg}"', env="conanrun")
ConanException: Error 1 while executing
$ echo $?   # → 1（非 0 = 负向测试已生效）

$ mv /tmp/backup <package_folder>/lib          # 恢复
# 同一命令回到 rc=0，41 项断言全过
```

## 适用范围

- **必然命中**：以 python-require / 纯脚本交付、且开发机会装同名分发包的包——pytest、
  iniconfig、packaging、pluggy、pygments 这类测试基础设施包。
- **可能命中**：任何 test_package 通过 `PYTHONPATH` 或 `PATH` 解析目标、而非用绝对路径直指
  产物文件的包。C/C++ 包若只按绝对路径调用二进制则不受影响，但一旦走 `PATH` 查名，
  同族问题就会出现（参见 DRAFT-coreutils-sha512sum-… 的 PATH 同名遮蔽）。
- **不受影响**：包名与任何可安装分发都不同名的纯 C/C++ 库。

## 判据速查

| 观察 | 结论 |
|---|---|
| 负向测试说 "fake test detected" 但正向断言全过 | 测试被环境里的同名物救活，先查 user site / PATH |
| `os.path.basename(realpath(dirname(mod.__file__))) == "<pkg>"` 是唯一来源断言 | **不是**来源校验，需补前缀比对 |
| 清空 PYTHONPATH 后 import 仍成功 | 存在回落路径（user site / 系统 site） |

## 与既有条目的关系

- **E427**「shadow CI 隔离 HOME 后不要只改 HOME；需给 Python 保留真实 site-packages」——
  同一个 user-site 回落机制的另一面：E427 讲"隔离 HOME 会让工具找不到依赖"，本条讲
  "没隔离干净会让测试找到不该找的依赖"。
- **DRAFT-coreutils-sha512sum-autotools-built-sources-test-package-path**（CLI 包 test_package
  须显式使用包内二进制绝对路径避免 PATH 同名遮蔽，R34/L1e）——**同族**：那条走 `PATH`
  遮蔽，本条走 `sys.path` 回落；两者都应遵守"测试必须绑定产物"这一合同。
- **DRAFT-E2175-static-pkg-ohos-artifact-test-link-assert**——把"测试绑定产物"做到
  ELF 层（断言 SONAME/INTERP/符号），与本条互补（那条验链接，本条验解析来源）。

## 查重声明

检索范围：`knowledge/graph`、`knowledge/drafts`、`knowledge/doc`、`knowledge/operations`。

- `PYTHONNOUSERSITE` → **0 命中**；`usersite` → **0 命中**；
  `sys.path`→user/`.local` 组合 → **0 命中**；`imported.*not.*packaged` → **0 命中**。
- `L1e` 关联命中 40 条、`R34` 120 条、`假通过` 41 条，已逐条比对最接近的 3 条：
  coreutils（PATH 遮蔽，非 sys.path）、opencsg（stub 测试未触达真能力）、E2175（ELF 层绑定）
  ——机制与修法均不同，本条不重复。
- 唯一 `来源校验` 字面命中为 `DRAFT-multipledispatch-version-metadata-reconciliation`
  （发行版本与模块 `__version__` 双来源一致性），与"导入来源"正交。
