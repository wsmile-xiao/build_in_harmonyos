# docopt 0.6.2 — 适配记录（HarmonyOS PC / arm64）

## 适配路径

`python-require` 纯 Python **单模块**库（`py_modules=['docopt']`，零运行时依赖）：

1. `source()` 取 PyPI 官方 sdist（sha256 校验）→ 下载上游测试文件；
2. `build()` 跑上游测试回填真实通过率（R51）；
3. `package()` 把顶层 `docopt.py` 拷进 `lib/python3.12/site-packages/`；
4. `package_info()` 用 `runenv_info/buildenv_info` 声明 PYTHONPATH。

> **注意**：docopt 不是包目录，是**单个模块文件**。`package()` 直接
> `shutil.copy2("docopt.py")`，不能按 `pathspec`/`jinja2` 那样 copytree。

## 无需源码补丁

py3.12 下 docopt 0.6.2 无 import 障碍，只有若干 `SyntaxWarning`：

```
docopt.py:165: SyntaxWarning: invalid escape sequence '\S'
    name = re.findall('(<\S*?>)', source)[0]
```

属非 raw 字符串字面量里的反斜杠（未来版本将报错，当前仅告警），
功能不受影响——上游测试 39 passed 已证实。故不打补丁。

## 上游测试：sdist 不含，须从 GitHub 官方 tag 取

docopt 的 `MANIFEST.in` 只有：

```
include README.rst LICENSE-MIT
recursive-include examples *.py
```

**测试文件没打进 PyPI 包**。仓库根目录实际有三组测试资产（GitHub tag
0.6.2 实测存在）：

| 文件 | 作用 | sha256（前 12） |
|---|---|---|
| `test_docopt.py` | pytest 单元/API 测试 | `7670233e466b` |
| `testcases.docopt` | 用例语料（`r"""..."""` + `$ cmd` / JSON 期望）| `ff1c967b929b` |
| `conftest.py` | 用例语料的收集器 | `0ddd77ede7a6` |

配方在 `source()` 中从 `raw.githubusercontent.com/docopt/docopt/0.6.2/`
下载这三者并**逐个校验 sha256**（同仓库 `antlr4-python3-runtime` / `adcli`
的构建期下载先例），下载失败的降级为 warning，不阻塞构建。

> 区分两种情形：**"上游确无测试"** vs **"上游有测试但 sdist 未打包"**。
> docopt 属后者——测试确实存在，只是不在 PyPI 包里，故不能按"无上游测试"
> 申报（R51 要求"上游确无测试"须附清点证据）。

### 两个测试组的口径差异

- `tests/test_docopt.py`：常规 pytest 文件 → **39 passed**。
- `tests/cases/testcases.docopt`：靠 `conftest.py` 的**旧式**
  `pytest_collect_file()` / `pytest.Item` 钩子把 `.docopt` 用例转成测试项
  → pytest 5.4.3 下 **164 passed**；pytest 9.x 已移除该旧 API，收集时报
  `TypeError: required field "lineno" missing from alias`。

因此把该 `conftest.py` 与 `.docopt` 隔离放进 **`tests/cases/` 子目录**：
常规测试文件单独运行时不会加载旧式收集器，稳定可跑；用例组作为
best-effort 附加执行（存在才跑）。

实测合计 **203 passed**，无失败。

## R38：不需要 commands.json

`setup.py` 无 `entry_points`、无 `scripts=`；sdist 无 `bin/` 产物；
`examples/` 只是示例脚本（不被安装）。纯库包 → 不创建 commands.json。

## 消费者契约（test_package）

`test_docopt_consumer.py` 覆盖：子命令 + 可重复参数（`ship new <name>...`）、
选项默认值（`--speed=<kn> [default: 10]`）、显式选项值、互斥组
（`--moored | --drifting`）、非法 argv 抛 `DocoptExit`，并直接驱动上游测试面
（`Option.parse`、`Required/OneOrMore/Argument.flat`、`parse_argv`）。
