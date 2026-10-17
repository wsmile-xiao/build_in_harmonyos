# typedload 2.41 适配笔记

## 0. 申报表（R51 上游测试三步法）

| 项 | 值 | 证据 |
|---|---|---|
| 上游来源 | https://codeberg.org/ltworf/typedload | PyPI `project_urls` / sdist `PKG-INFO` |
| 版本 | 2.41（sdist `PKG-INFO: Version: 2.41`） | `pyproject.toml:3 version = "2.41"` |
| 许可 | GPL-3.0-only | `pyproject.toml:12`、`PKG-INFO` |
| 语言 / 形态 | python（纯 Python，`py3-none-any`，无 C 扩展） | 源码 25 个文件全部 `.py`，主体占比 100% |
| 构建系统 | setuptools + wheel（`pyproject.toml [build-system]`） | `requires = ["setuptools", "wheel"]` |
| 上游测试入口 | `tests/` 15 个 `test_*.py`，全部 `import unittest`；**无 pytest 配置** | `python3 -m unittest discover -s tests` |
| 测试用例数 | **212**（实测 `Ran 212 tests`） | `<build>/upstream-unittest-verbose.log` |
| 第三方测试依赖 | `attrs`（仅 `tests/test_attrload.py` 顶层导入；`test_literal.py:110`、`test_typealias.py:25` 为函数内可选导入） | `grep -rn "from attr" tests/` |
| 运行时依赖 | **0**（`PKG-INFO` 无 `Requires-Dist` 行） | `PKG-INFO` / `pyproject.toml` 均无 dependencies |
| 补丁 | **无**（`patches: {}`） | 全量测试零失败，无必要改动上游 |

## 1. 环境

- 目标：`aarch64-linux-ohos`（profile `ci/conan/profiles/ohos-aarch64`）
- 解释器：OHOS 平台 python **3.12.9**（`sys.platform == "ohos"`、
  `sysconfig.get_platform() == "ohos-aarch64"`、`platform.system() == "HarmonyOS"`、
  `uname.release == "HongMeng Kernel 1.12.0"`）
- conan 2.29.1（OHOS 适配版）；remote `ohpcd`

## 2. 为什么按 `python-require` 打包（而不是「不能适配」）

typedload 是**纯 Python** 库：无 C 扩展、无 pybind11、`py3-none-any` wheel。
它在 OHOS 上的「适配」= 把模块按 OHOS python3.12 的 purelib 布局发布出去，
并保证上游测试在 OHOS 解释器上真实可跑。本仓已有 127 个 `python-require`
配方（`typepy`、`jinja2`、`attrs`、`dominate`…），本包沿用同一模式，未引入新约定。

## 3. 打包实现

```python
package_type = "python-require"
settings = "os", "arch", "compiler", "build_type"

def requirements(self):
    pass                      # 运行时零依赖（PKG-INFO 无 Requires-Dist）——刻意留空

def build_requirements(self):
    self.tool_requires("attrs/26.1.0")   # 仅测试期，不传播给消费者

def package(self):
    # typedload/（12 个文件：__init__.py/.pyi、py.typed、dataloader/datadumper/
    # typechecks/alias/helpers/name_manglers/moretypes/exceptions）
    #  -> <pkg>/lib/python3.12/site-packages/typedload
    # 强制校验 py.typed / __init__.pyi（上游 setup.py package_data 声明）
```

`package_info()` 用 `runenv_info` + `buildenv_info` 追加 `PYTHONPATH`
（aiohttp 教训：只 print 不生效，消费者会 `No module named typedload`）。

## 4. 上游测试真实执行（R51）

```bash
# 命令（conanfile.py build() 内，真实执行）
cd <src> && PYTHONPATH=<src>:<attrs-site> PYTHONDONTWRITEBYTECODE=1 \
    python3 -m unittest discover -s tests -v
```

实测（`<build>/upstream-unittest-verbose.log`，逐用例名单见该文件）：

```text
Ran 212 tests in 0.2xx s
OK
```

| 指标 | 值 |
|---|---|
| 用例总数 | 212 |
| 通过 | **212** |
| 失败 | 0 |
| 错误 | 0 |
| 跳过 | **0** |

**对照实验（证明「不跳过、不凑数」）**：不提供 `attrs` 时实测
`Ran 187 tests` + `FAILED (errors=1)`（`tests/test_attrload.py` 收集期
`ModuleNotFoundError: No module named 'attr'`）——
即 25 个用例会因缺依赖被吞掉。因此配方**硬性**以 `tool_requires("attrs/26.1.0")`
补齐，并让「依赖解析失败」直接抛 `ConanException`。

15 个测试文件（全部真实执行，无遗漏）：
`test_attrload.py`、`test_dataclass.py`、`test_datadumper.py`、
`test_dataloader.py`、`test_datetime.py`、`test_deferred.py`、
`test_dumpload.py`、`test_exceptions.py`、`test_legacytuples_dataloader.py`、
`test_literal.py`、`test_moretypes.py`、`test_name_manglers.py`、
`test_typealias.py`、`test_typechecks.py`、`test_typeddict.py`

> 上游 test_package 不能替代上游测试统计：两者都跑，且分别申报（见 §5）。

## 5. test_package（消费者视角，17 用例，含鸿蒙专有 3）

| # | 用例 | 归属 |
|---|---|---|
| 1 | `ohos_platform_identity` | **鸿蒙专有** |
| 2 | `ohos_purelib_layout_site_packages` | **鸿蒙专有** |
| 3 | `ohos_path_roundtrip` | **鸿蒙专有** |
| 4 | `payload_is_packaged_pure_python` | 打包契约 |
| 5 | `type_markers_shipped`（py.typed / __init__.pyi） | 打包契约 |
| 6 | `zero_runtime_dependencies`（子进程核验未加载非 stdlib 顶层模块） | 打包契约 |
| 7 | `version_marker_moretypes` | 打包契约 |
| 8 | `dataclass_roundtrip`（含 `hidedefault` 语义） | 上游 API |
| 9 | `namedtuple_and_enum` | 上游 API |
| 10 | `containers_roundtrip` | 上游 API |
| 11 | `optional_union_literal` | 上游 API |
| 12 | `typeddict_load` | 上游 API |
| 13 | `scalars_datetime_uuid_ip_pattern` | 上游 API |
| 14 | `moretypes_hexrgb` | 上游 API |
| 15 | `negative_wrong_type_raises` | 负例 |
| 16 | `negative_missing_field_raises` | 负例 |
| 17 | `negative_bare_generic_raises` | 负例 |

鸿蒙专有 3 项的具体断言：

1. `ohos_platform_identity`：`sys.platform == "ohos"`、
   `sysconfig.get_platform().startswith("ohos")`、`platform.machine() == "aarch64"`、
   `uname.system` 含 `HarmonyOS`（或 `uname.version` 含 `HongMeng`）。
2. `ohos_purelib_layout_site_packages`：site-packages 目录必须以
   `lib/python3.12/site-packages` 结尾，且 `typedload` 恰好落在其中——
   对齐 OHOS python3.12 的 purelib 约定（否则 OHOS 解释器不会命中）。
3. `ohos_path_roundtrip`：OHOS 真实路径
   `/storage/Users/currentUser/tmp/typedload-2.41.log` 与
   `/data/storage/el2/base/cache/typedload.json` 经 `pathlib.Path` 处理器
   `load`/`dump` 往返一致。

## 6. 源码修改

**无**（`patches: {}`）。2.41 在全量 212 用例下零失败，无平台相关失败项，
不做任何上游文件改动（R1/R8：不为「看起来适配过」而加无实质逻辑的平台宏）。

## 7. 踩坑与真值（消费者测试首轮 3 处断言错误的修正过程）

首轮把断言按「直觉」写，实测 3 处与上游语义不符，逐一按真实行为修正：

| 现象 | 真值 | 处理 |
|---|---|---|
| `load([1,2], list)` 报 `TypedloadTypeError: Cannot deal with value of type list` | typedload **不支持裸泛型**，必须 `list[int]`（文档 Supported types） | 改为参数化泛型；并新增负例 `negative_bare_generic_raises` 固化该语义 |
| `dump(用户 dataclass)` 少了 `shell` 字段 | `Dumper` 默认 `hidedefault=True`，会省略等于默认值的字段 | 断言默认省略 + `dump(..., hidedefault=False)` 完整往返两种语义 |
| `load(1.5, int)` 不报错 | typedload 对数值做**合法转换**（`1.5→1`、`123→'123'`） | 从负例中移除，负例改用真正非法的 `"abc"→int`、`None→int`、Literal 越界、`dict[str,int]` 值非法 |

教训：纯 Python 库的「适配」风险不在编译，而在**测试断言的语义真值**——
必须先用上游真实行为校准，再写断言（否则会写出「自证正确」的假测试）。

## 8. 验证结果（真实命令 / 退出码 / 日志）

```bash
# ① 真实构建（与 CI 完全一致的命令）
conan create archives/t/typedload/2.41 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="typedload/*"
# → RC=0；typedload/2.41: Package '6b129b06...' created
#   上游测试：Ran 212 tests | passed=212 failed=0 errors=0 skipped=0 | OK
#   消费者测试：typedload consumer API: 17/17 passed
#   依赖：日志中除 typedload/2.41 外无任何 "Calling build()" → 零源码编译
#   （attrs/26.1.0 以 conan download 先行验证可消费，RC=0）

# ② 配方门禁
python3 scripts/ohc-run.py conan-verify typedload 2.41      # → RC=0（G0-G4 + L2/L4/L5 全 PASS）

# ③ 收尾（W2 结构 + R36 依赖 + W3 本地 CI 模拟）
python3 scripts/ohc-run.py finish typedload 2.41 built
```

### 关于 `finish` step [3/10] G0（非阻塞）

G0 干净构建验证是为 **autotools** 包设计的（直接 `./configure`）。typedload 是
纯 Python 包，源码树**没有** `./configure`，故 G0 必然 `exit 127`
（`g0-configure.log`）。该步骤在本 SKILL 中标注为**非阻塞**，且等价的
「干净构建验证」由 conan-verify 的 G2（从干净源码 `conan create`）承担——已 PASS。
与 `tomli`、`jinja2` 等既有纯 Python 包一致，未新增 `.g0-*` 标记文件。

### 关于 `finish` step [5/10] W3 的 junk_check 模式

W3 在**未提交**状态下运行，`junk_check.sh` 的 `incremental` 模式
（`git diff origin/main...HEAD`）为空 → 回退 `full` 模式（`git ls-files`）→
扫到 **main 上的存量垃圾**（与本包无关，`git ls-tree origin/main` 可证）：

```text
[FAIL] JC1/JC5: 5 个运行时状态文件被跟踪
  archives/c/cloog/0.21.1/.build-closed
  archives/c/cloog/0.21.1/.staging-verified
  archives/k/kics/2.1.20/.staging-verified
  archives/l/libbfio/20260623/.staging-verified
  archives/t/thc/3.8/.staging-verified
```

本包自身在 CI 实际使用的 **prdiff 模式**下 JC 全绿：

```text
JUNK_PR_DIFF=<本 PR 文件清单> bash ci/scripts/junk_check.sh
  → Junk Files: 0 / JC_RESULT=pass / JC6 涉及软件数: 1（合规）
```

即：本 PR 未引入任何垃圾文件；`full` 模式失败是 main 分支的存量问题
（5 个文件、4 个包），已在任务结果中单独上报。

## 9. submit 就绪预检三项（已全部就绪）与 staging 验证方式

`finish` step [10/10] 检查 `reports/test-report.md`、`packaging/`、`.staging-verified`
三项。三项均已就绪，且**后两项记录了真实的验证证据**（非空壳标记）：

| 检查项 | 本包情况 | 证据 |
|---|---|---|
| `reports/test-report.md` | ✅ 已创建 | `reports/test-report.md`（上游 212 + 消费者 17 用例明细） |
| `.staging-verified` | ✅ 已创建（含证据） | `verified=0 failed=0` —— driver Step8 语义下本包 **无 `bin/*` 可执行文件**（纯 Python 库）；改以**真实的 staged 安装 + 消费者导入**验证交付物可用（见下） |
| `packaging/.packaged` | ✅ 已创建（含证据） | 交付物 = `conan create` 产出的 conan 包（`package_type=python-require`）；标记内记录 recipe_revision / package_id / package_folder / `conanmanifest.txt` sha256 |

### staging 验证（真实执行，非空壳）

```bash
# ① staged 安装（消费者视角）
conan install --requires=typedload/2.41 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -g VirtualRunEnv -of <staging-dir>                       # → rc=0

# ② 从 staged 环境导入（同时验证 package_info() 的 runenv PYTHONPATH 真的生效）
source <staging-dir>/conanrun.sh
PYTHONDONTWRITEBYTECODE=1 python3 -c "import typedload, typedload.moretypes"
# PYTHONPATH=<pkg>/lib/python3.12/site-packages
# → import ok -> .../typedload/__init__.py
# → typedload.moretypes.HexRGB('#00ff00').value = 65280      # → rc=0
```

> 说明：`packaging/` 与 `.staging-verified` 是 v3.0 之前的 legacy 装载路径
> （autotools + `DESTDIR` staging + `<name>-<ver>-ohos-aarch64.tar.gz`）；
> 本包以 `conanfile.py` 交付，legacy 的 tarball 不存在，故标记内改用 conan 包的
> 等价证据（revision / package_id / manifest sha256 / staged 导入结果）。
> 两个标记均在 `.gitignore` 中，**不会进入 PR**，只反映本地 finish 状态。
> `archives/a/attrs/26.1.0`（同为 python-require + conanfile.py）亦有 `packaging/.packaged` 先例。

### 消费者注意事项（实测发现）

从 conan 缓存包目录 `import typedload` 时，CPython 会把 `__pycache__/*.pyc`
写进该包目录（本包 test_package 已用 `PYTHONDONTWRITEBYTECODE=1` 规避）。
消费者如需保持包目录只读/干净，请同样设置该变量。

（`reports/`、`.staging-verified`、`packaging/.packaged`、`.build-closed`、
`test_package/conan*.sh` 均在 `.gitignore` 中，不会进入 PR。）

## 9.1. 交付物清单（PR 原子性）

本次共 **9 个文件**进入 PR：`archives/t/typedload/2.41/**`（7 个）+
`knowledge/drafts/`（1 组知识草稿，kv+md 一一对应，2 个）：

```text
archives/t/typedload/2.41/conanfile.py
archives/t/typedload/2.41/conandata.yml
archives/t/typedload/2.41/manifest.yaml
archives/t/typedload/2.41/notes.md
archives/t/typedload/2.41/test_package/conanfile.py
archives/t/typedload/2.41/test_package/MANIFEST.yml
archives/t/typedload/2.41/test_package/test_typedload.py
knowledge/drafts/typedload-2.41-pure-python-conan-adaptation-pattern.kv
knowledge/drafts/typedload-2.41-pure-python-conan-adaptation-pattern.md
```

> 说明：**软件级** `archives/t/typedload/{manifest.yaml,README.md}` 按 PF9 分支/路径闸
> 口径（`archives/` 变更须落在 `archives/<字母>/<包>/<版本>/` 层）**不进入 PR**，
> 仅作为本地 AI 元数据保留；`submit` 的暂存范围亦仅为版本目录 + `knowledge/drafts/`。

（`.build-closed` / `reports/` / `test_package/conan*.sh` / `.ci-result.json` /
`packaging/.packaged` / `.staging-verified` / `.verify-passed` 均由 `.gitignore` 忽略，
不会进入 PR；未改动任何框架文件。）
---

**编译结束**: 2026-10-04 13:33
**最终状态**: built
