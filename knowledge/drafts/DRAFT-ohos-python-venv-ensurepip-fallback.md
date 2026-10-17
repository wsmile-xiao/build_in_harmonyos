# DRAFT-ohos-python-venv-ensurepip-fallback — OHOS Python 缺 ensurepip 时 `python -m venv` 直接失败，「本地绿 CI 红」

> Contributor: 3211 / Status: **DRAFT** / Updated: 2026-09-20 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-python-venv-ensurepip-fallback`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E544` setuptools 构建的 Python C 扩展包 CI 四重适配链 | 已收录 | pillow 16 轮实证：二进制 diff、**缺 setuptools**、链接器、签名四层 | E544 层 2 是「**裸 HNP python 没有 setuptools**」，对策是 `pip install --target` 自举 **setuptools**；本条是**没有 ensurepip**（pip 本身装不上），发生在**更前一步——vev 创建阶段**。两者的修补对象不同：E544 补 setuptools（pip 已可用），本条补 pip（连 venv 都建不出来）。同一适配里二者会**先后**出现：先过不了 venv，才轮到 setuptools |
| `E543`（numpy/meson）OHOS Python C 扩展必须用 Conan Python 头/库路径 | 已收录 | 用哪个 Python 构建 C 扩展；test_package 用 **ensurepip** + 官方固定 wheel 的 SHA-256 校验安装 pytest | E543 **假定 ensurepip 可用**（其方案就建立在 ensurepip 之上）；本条指出该前提在部分 OHOS Python 上**不成立**，并给出不依赖 ensurepip 的等价路径。二者互补：E543 管「用哪个解释器」，本条管「这个解释器能不能自举出 pip」 |
| `E512` 纯 Python 包 build() 自检 import，宿主预装而 CI 缺失 → 本地过 CI 挂 | 已收录 | 依赖缺失导致 `ModuleNotFoundError` | 同属「本地绿 / CI 红」现象族，但成因不同：E512 是**缺一个包**（补依赖可解），本条是**解释器能力缺失**（补依赖无从下手，只能换 pip 来源）。诊断方向相反：E512 去装包，本条去绕开 ensurepip |
| `DRAFT-ohos-test-subprocess-overrides-pythonpath-needs-venv` | 草稿 | 子进程整体覆盖 PYTHONPATH → 注入失效，须改用独立 venv | 那条**主张**用 venv（并给出了理由）；本条指出该方案在一个未言明的前提上会**建不起来**，是它的必要补充。werkzeug 适配中顺序命中：先因前者改用 venv，再因本条修复 venv 的创建 |
| `DRAFT-ohos-pythonpath-entry-skips-pth` | 草稿 | PYTHONPATH 上的包只提供顶层 import、不执行 `.pth` | 同属「Python 环境搭建的隐形前提」族（那条管 import 语义，本条管解释器自举能力），互不重复 |

**全库查证**：对 `ensurepip`、`--without-pip`、`venv`+`pip 自举` 三组关键词在
`knowledge/graph/*.kv`、`knowledge/doc/*.md`、`knowledge/drafts/*.kv`
中检索——**`knowledge/graph/` 命中 0 条**，`drafts/` 无任何以 venv/ensurepip
为主题的条目。仓内 `trove-classifiers`（`venv --without-pip`）、
`acme-tiny-pyc`（记 CI 无 ensurepip）、`fastconstmap`（`ensurepip --root`）
三处先例均只是**个案 notes/manifest**，未沉淀为知识条目。

## Scope（何时用）

| 信号 | 检查命令 |
|---|---|
| 构建/测试期建 venv 以跑上游套件或装构建依赖 | `grep -n '"venv"' <recipe>` |
| 报 `-m ensurepip ... returned non-zero exit status 1` | 直接观察报错 |
| 报「could not create the test virtualenv」一类包装错误 | 观察报错 |
| **同一 commit 本地全绿、CI 全红** | 对照两处解释器（见下） |

> ⚠️ 判定关键：**不要只看 `import ensurepip` 是否成功**——模块在、wheel 不在是常态。
> 必须看 `_bundled` 目录内容：
> ```bash
> python3 -c "import ensurepip, os; d=os.path.join(os.path.dirname(ensurepip.__file__),'_bundled'); print(d, os.path.isdir(d) and os.listdir(d) or 'MISSING')"
> ```

## Symptom（真实表现）

werkzeug 3.1.8 适配（CI #54104）：本地 `conan create` 全绿（**967 passed**），
CI 在 `build()` 内建测试 venv 时即失败，**上游用例 0 条执行**：

```
werkzeug/3.1.8: ERROR:
Package '32e624f602c55e90154ccacd2fd4d239bf9c6f63' build failed
ERROR: werkzeug/3.1.8: Error in build() method, line 312
        self._run_upstream_tests()
while calling '_run_upstream_tests', line 237
        py, _site = self._build_test_venv()
while calling '_build_test_venv', line 169
        raise ConanException(
ConanException: could not create the test virtualenv (R51: refusing to report an unrun suite as passing). Tail:
Error: Command '[...]/test-venv/bin/python3', '-m', 'ensurepip', '--upgrade', '--default-pip']' returned non-zero exit status 1.
```

**最有价值的信息是最后一行，但它出现在「包装错误」的 Tail 里**——外层说的是
「venv 建不出来」，真因（解释器缺 ensurepip）若不看 Tail 就完全看不到。

### 为什么「本地绿、CI 红」

| 解释器 | `_bundled/pip-*.whl` | `python -m venv` |
|---|---|---|
| 开发机 `/storage/.../usr/local/bin/python3` | ✅ 有（`pip-24.3.1-py3-none-any.whl`） | ✅ 成功 |
| CI worker 的 HNP python | ❌ 无 | ❌ `ensurepip` 报 returncode 1 |

同一份代码、同一个 commit、换台机器结论相反 → 极易被误判成 flaky / 平台故障 /
worker 网络问题而反复重跑，掩盖真实的环境前提缺失。

## Root Cause

`python -m venv <dir>` 的默认行为里包含一步 `ensurepip --upgrade --default-pip`
——把 pip **安装进新 venv**。OHOS 上的 Python 常常**没有可用的 ensurepip**
（`ensurepip/_bundled/` 下 pip wheel 缺失），该步骤失败，venv 根本建不出来。

只有三层要点：
1. **失败发生在 venv 创建阶段**，不是测试阶段 → 套件一条没跑；
2. **真因被包装错误掩盖**（外层说「venv 建不出来」）；
3. **只在一部分解释器上出现** → 本地绿、CI 红。

> 另一形态：直接 `python -m ensurepip` 自举 pip 同样失败（同一个缺 wheel 的原因），
> 所以「先用 ensurepip 装 pip，再建 venv」也走不通——**只能绕开 ensurepip**。

## Recommended Solution

**一律 `--without-pip` 直接建 venv，建完当场实测解释器能启动。**

⚠️ 一个真实的反面教训：本条第一版推荐的是「先试常规 venv、失败才回退」，**而那
正是后来 CI 上失败的做法**。带 pip 的常规 venv 会因 ensurepip 不可靠而**中途
失败**，留下残缺骨架；再对半成品 `--clear` 重建，就产出了「目录齐全、
`bin/python` 也在，却解释器起不来」的坏 venv。故现在改为**一步到底**：

```python
def build_with(cmd, label, extra_env=None):
    """建 venv 并当场验证解释器能启动；返回是否可用。"""
    shutil.rmtree(venv_dir, ignore_errors=True)          # 不留半成品
    res = self._run(cmd, timeout=900, extra_env=extra_env)
    if res.returncode != 0 or not os.path.isfile(py):
        return False
    # ★ 关键：rc==0、bin/python 存在，都不等于该解释器能跑
    boot = self._run([py, "-c", "import encodings, sys; print(sys.prefix)"],
                     timeout=300)
    if boot.returncode != 0:
        self.output.info(f"{label}: interpreter cannot start — {self._tail(boot)}")
        return False
    self.output.info(f"{label}: interpreter ready ({boot.stdout.strip()})")
    return True

# ① 一步到底，彻底绕开 ensurepip
if not build_with([sys.executable, "-m", "venv", "--without-pip", venv_dir],
                  "venv --without-pip"):
    # ② 换 virtualenv（另一套独立实现，也是本包 test 依赖里已声明的一项）
    tools = ...; self._run([sys.executable, "-m", "pip", "install", "--target",
                            tools, "--index-url", PIP_INDEX, "virtualenv"], ...)
    if not build_with([sys.executable, "-m", "virtualenv", "--no-seed", venv_dir],
                      "virtualenv --no-seed", extra_env={"PYTHONPATH": tools}):
        raise ConanException("could not create a usable test virtualenv (R51)…")

# ③ venv 自身此刻【没有 pip，无法自举】→ 必须用【外层】解释器的 pip
os.makedirs(site, exist_ok=True)
res = self._run([sys.executable, "-m", "pip", "install", "--no-deps",
                 "--target", site, "pip"], timeout=900)
check = self._run([py, "-m", "pip", "--version"], timeout=300)   # ④ 实测
if check.returncode != 0:
    raise ConanException("bootstrapped pip is not usable …")
```

**四个关键点**：

1. **`--without-pip` 一步到底** —— 不留「先失败一次」的半成品骨架，也不对
   半成品做 `--clear`。这是 CI 上坏 venv 的来源。
2. **必须实测解释器能否启动**，不能用 rc / 文件存在性代替。坏 venv 的报错形态是
   `Fatal Python error: init_fs_encoding ... No module named 'encodings'` 且
   `sys.prefix` 指向 base；省掉这步会把「venv 没建好」伪装成「pip 不可用」。
3. **必须用外层解释器的 pip 自举** —— venv 内的 python 此刻没有 pip，
   `py -m pip install pip` 无从谈起（实测：`--without-pip` 建的 venv 里
   `import pip` → `ModuleNotFoundError`）。`--target` 指向 venv 的 site-packages
   后即可正常使用（实测 `pip 26.2.1 from <venv>/lib/python3.12/site-packages/pip`）。
4. **保留 venv 隔离** —— venv 本体、被测包、上游用例都没变，只换了 pip 的来源。
   测试真实性与隔离性均**不降级**，故优于「改用系统解释器直装」或「跳过用例」。
   另：执行环境顺手清掉 `PYTHONHOME`（同样会把 venv 的 stdlib 定位带偏）。

### 回退方案（priority 2）：virtualenv `--no-seed`

`venv --without-pip` 未能产出**可启动**的解释器时，改用 **virtualenv**：

```bash
python3 -m pip install --target <tools> virtualenv
PYTHONPATH=<tools> python3 -m virtualenv --no-seed <venv_dir>
```

`--no-seed` 不种 pip（pip 仍由外层自举），也免去对 wheel 的依赖。之所以它是
**真正不同**的兜底而非重复：virtualenv 与 stdlib `venv` 是两套独立实现，env
布局、pyvenv.cfg 写法与 stdlib 定位各异；实测本平台可正常产出可启动的 venv
（`created virtual environment CPython3.12.9 ...`，解释器 `import encodings`
正常、自举 pip 后 `pip --version` 正常上报）。二者皆不可用才抛错，不得静默降级。

## 反面模式（forbid）

| 模式 | 为什么禁止 | 后果 |
|---|---|---|
| 因 ensurepip 缺失就退化为「系统解释器直装测试依赖」 | 会把测试依赖、被测包、宿主环境混在一起（PYTHONPATH/版本污染） | 隔离性丢失，宿主污染型假通过/假失败接踵而至；后人被误导为「OHOS 不能建 venv」 |
| 把 venv 创建失败记成通过 / 静默跳过 | venv 建不出来 = 套件一条未跑，属 R51 失真 | 通过率虚高，真实修法（`--without-pip` + 自举）被埋没 |
| **凭 rc==0 / `bin/python` 存在就判定 venv 可用** | rc 与文件存在性都**不能**证明解释器能启动；本平台出现过「目录齐全却起不来」（`No module named 'encodings'`，`sys.prefix` 指向 base） | 失败推迟到后面某次 pip 调用才爆，报成「pip 不可用」，把根因彻底掩盖，诊断被误导到 pip/网络方向 |
| **先试带 pip 的常规 venv、失败再 `--clear` 重建** | 带 pip 的 venv 会因 ensurepip 不可靠而中途失败留下残缺骨架；对半成品重建属两段式构造 | 产出状态不一致的坏 venv（CI 实证），极难查 |

## 单库实证

| 项 | 值 |
|---|---|
| 案例 | werkzeug 3.1.8（纯 Python，需真实运行上游 pytest 套件） |
| 环境 | HarmonyOS PC / OpenHarmony，aarch64-linux-ohos，CI worker |
| 现象①| 本地 `conan create` 全绿（967 passed）；CI #54104 建 venv 即失败，**上游 0 条执行**（`ensurepip ... returned non-zero exit status 1`） |
| 现象②| 加上「先试常规 venv 再回退」后，CI 仍失败，且更隐蔽：`bootstrapped pip is not usable inside the test venv` + `init_fs_encoding ... No module named 'encodings'`，`sys.prefix` 指向 **base** ——**本条第一版推荐的正是这个失败做法** |
| 复现 | 移走 `<python>/lib/python3.12/ensurepip/_bundled/pip-*.whl`，则普通 `python -m venv` 报出与 CI **逐字相同**的 `ensurepip ... returned non-zero exit status 1` |
| 修法 | `venv --without-pip`（一步到底）→ **实测 `import encodings`** → 失败则 `virtualenv --no-seed` → 外层 pip `--target <venv site-packages> pip` → `pip --version` 复检 |
| 修复后 | 在**该失败条件仍在**的情况下 `conan create` **exit 0**：日志 `venv --without-pip: interpreter ready (...)`，上游 **967 passed / 1 skipped / 1 deselected**，消费者测试 **22/22** |
| 收尾 | 移走的 wheel 已复位，重新建 venv 验证 `pip 24.3.1` 恢复正常 |

## 测试覆盖边界

- 本条解决的是**环境搭建**问题，不改变测试口径：上游用例数与断言均未变
  （werkzeug 967 passed，与本地一致）。
- 「1 deselected」是 AF_UNIX 用例（平台限制，见 `E024`），与本条无关。
- 兜底路径（virtualenv）**仅在 `venv --without-pip` 未产出可启动解释器时进入**——
  故不影响既有通过路径。
- 本条的复现依赖「移走 wheel」这一非常规操作；生产环境的等价条件是
  「解释器本来就不带 `_bundled` wheel」，CI worker 上实测如此。

## 关联

- `E544` — 裸 HNP python 缺 **setuptools**（本条缺 **ensurepip**；同一条 CI 适配链的相邻两层）
- `E543` — 假定 ensurepip 可用（本条指出该前提不成立，并给出不依赖它的路径）
- `E512` — 宿主 vs CI 依赖差异导致「本地过、CI 挂」（同族现象，成因不同）
- `DRAFT-ohos-test-subprocess-overrides-pythonpath-needs-venv` — 主张用 venv（本条保证 venv 能建出来）
- `DRAFT-ohos-pythonpath-entry-skips-pth` — 同属 Python 环境搭建的隐形前提
