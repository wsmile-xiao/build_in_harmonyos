# jinja2 3.1.6 适配笔记

## 编译环境

- 目标：`aarch64-unknown-linux-ohos`（profile: `ci/conan/profiles/ohos-aarch64`）
- Python：3.12（宿主解释器；纯 Python 包，无 ABI 绑定）
- conan 2.29.1
- 构建系统：上游 `flit_core`（pyproject.toml），**src 布局**

## 本包为何存在 / 与 2.10.1 的关系

`jinja2` 是本仓**已有包**（main 上为 `2.10.1`），本 PR 是**版本升级到 3.1.6**，
不是新增包。升级动机是 2.10.1 在 Python 3.12 上存在两处历史包袱：

| 项 | 2.10.1 | 3.1.6 |
|---|---|---|
| `collections.Mapping` 等旧别名 | 从 5 处 import（py3.10 已移除）→ **无法 import**，需补丁 | 已消除 → **无需补丁** |
| `soft_unicode` | utils.py 依赖 MarkupSafe<2.1 的该 shim → 必须钉 markupsafe **1.1.1** | 已移除（两处 `soft_unicode` 均不存在）→ 可用 **MarkupSafe>=2.0** |
| 上游实测 | 533 passed / **2 failed / 1 error** / 3 skipped | **909 passed / 0 failed** |
| 布局 | setuptools 平铺（`jinja2/`） | **src 布局**（`src/jinja2/`）+ flit_core |

即 3.1.6 消除了 2.10.1 那三项环境相关失败，**零失败**。

## 编译步骤

```bash
# 1) 取源码 + 校验 sha256（conandata.yml，PyPI 官方 URL）
# 2) build()：从平台 pip 镜像取测试依赖（pytest>=7 + trio）到独立目录，
#    再以该目录 + src/ + markupsafe-site 为 PYTHONPATH 跑上游 pytest（R51）
# 3) package()：src/jinja2 → <pkg>/lib/python3.12/site-packages/jinja2
# 4) package_info()：runenv_info + buildenv_info 声明 PYTHONPATH
```

## 遇到的问题与解决方案

### 问题 1：宿主 pytest 5.4.3 与 py3.12 不兼容

直接 `python3 -m pytest` 报：

```text
File ".../_pytest/assertion/rewrite.py", line 330, in _rewrite_test
    co = compile(tree, fn, "exec", dont_inherit=True)
TypeError: required field "lineno" missing from alias
```

即宿主 5.4.3 的**断言重写钩子**与 py3.12 的 AST 不兼容（与 2.10.1 当初用
`--assert=plain` 绕过的同一根因）。

**修法**（按 setuptools 84.0.0 先例）：构建期从平台 pip 镜像取**新版**
pytest + trio 到独立目录，再以该目录为 `PYTHONPATH` 运行，不依赖宿主版本：

```python
UPSTREAM_TEST_REQUIRES = ("pytest>=7", "trio")
PIP_INDEX = "https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple"
# 与 CI 一致（ci/conan/setup.sh:55 的 PIP_COMMUNITY_INDEX）
```

**取依赖失败显式抛 `ConanException`**，不静默降级（杜绝「测试没跑但构建成功」）。

### 问题 2：pip 索引 URL 容易写错

平台镜像的路径是 `.../pypi/-/packages/simple`（含 `-/packages/`），
写成 `.../pypi/simple` 会 `HTTPError`、pip 报
`Could not find a version that satisfies the requirement pytest>=7 (from versions: none)`。
**以 `ci/conan/setup.sh:55` 的 `PIP_COMMUNITY_INDEX` 为准**。

### 问题 3：src 布局（与 2.10.1 的打包路径不同）

3.1.6 的包在 `src/jinja2/`，不是仓库根的 `jinja2/`。若照抄 2.10.1 的
`package()` 会找不到源码。**修法**：`package()` 从
`<source>/src/jinja2` 取，并在 `build()` 中先校验该目录存在。

### 问题 4：升级后必须重新核对「旧版为何钉死某依赖版本」

2.10.1 把 markupsafe 钉在 1.1.1，原因是 `jinja2/utils.py` 使用
`soft_unicode`（MarkupSafe 2.1 起移除）。**3.1.6 已移除该 shim**——实测：

```text
hasattr(markupsafe, "soft_unicode")      → False   （markupsafe 3.0.3）
hasattr(jinja2.utils, "soft_unicode")    → False
```

故本版本改声明 `MarkupSafe>=2.0`，用 ohpcd 已发布的 `markupsafe/3.0.3`。
**教训**：大版本升级时不要照抄旧 pin，也不要误留旧版的兼容代码。

### 问题 5：`jinja2.sandbox` 是子模块，且沙箱断言不能凭直觉写

消费者测试最初写 `jinja2.sandbox.SandboxedEnvironment` → 报
`AttributeError: module 'jinja2' has no attribute 'sandbox'`（`__init__` 未导入
该子模块）。改为显式 `from jinja2.sandbox import ...`（上游
`tests/test_api.py:29` 同款）。

进一步，断言不能写 `{{ ''.__class__ }}`——**实测该表达式在 3.1.6 下不抛
SecurityError**，用它做负例是错的。改用上游 `tests/test_security.py:60` 的
惯用法：`ImmutableSandboxedEnvironment` 下对内置容器的**变异方法**
（`{{ [].append(23) }}` / `{{ [].clear() }}` / `{{ [1].pop() }}`）必须抛
`SecurityError`。

### 问题 6：`--basetemp` 必需

OHOS 上新建目录属主被文件系统强制显示为挂载属主（20001006），与进程 uid
不一致 → pytest 默认 `<tmp>/pytest-of-<user>` 的属主检查必然
`INTERNALERROR: not owned by the current user`。传 `--basetemp` 走
`_given_basetemp` 分支绕过（meson / setuptools 先例）。

### 问题 7：屏蔽宿主插件

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`：宿主 site-packages 的插件（pyfakefs 等）
与 py3.12 不兼容，自动加载会在 import 期崩。

## 源码修改

**无**（`patches: {}`）。3.1.6 已是 py3.12 兼容版本，未改动任何上游文件。

## 依赖版本

| 包 | 版本 | 类型 | 说明 |
|----|------|------|------|
| markupsafe | 3.0.3 | requires（运行时） | pyproject: `dependencies = ["MarkupSafe>=2.0"]` |

测试依赖（未发布 ohpcd，构建期从平台 pip 镜像取）：`pytest>=7`、`trio`
（来自上游 `requirements/tests.in`）。

## 验证结果

```bash
# 上游测试套件
PYTHONPATH=<test-deps>:<src>:<markupsafe-site> python3 -m pytest tests -q
# → 909 passed in 4.21s

# 完整本地验证（与 CI 相同 profile + 相同参数）
conan create archives/j/jinja2/3.1.6 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
# → EXIT CODE=0
#   [upstream] 909 passed in 4.55s
#   Package '32e624f602c55e90154ccacd2fd4d239bf9c6f63' created
#   jinja2 3.1.6 consumer API: 15/15 passed
```

- 上游测试：**909 passed / 0 failed / 0 skipped**（100%，与 2.10.1 的
  2 failed + 1 error 形成对比）
- 消费者测试：**15/15 passed**

## 注意事项

1. **测试依赖必须从平台 pip 镜像取新版**：宿主 pytest 5.4.3 与 py3.12 不兼容，
   不要依赖宿主版本（也不要再退回 `--assert=plain` 的老绕过方式）。
2. **pip 索引 URL**：`.../pypi/-/packages/simple`（以 `ci/conan/setup.sh:55` 为准）。
3. **src 布局**：打包路径是 `src/jinja2`，不是仓库根。
4. **markupsafe pin 的变化是刻意的**：3.1.6 不再需要 1.1.1，改成 `>=2.0`；
   不要照抄 2.10.1 的 pin。
5. **本包无补丁**：与 2.10.1 需要 `0001-collections-abc.patch` 不同。
6. 消费者测试中 `jinja2.sandbox` 需显式 import；沙箱负例用容器变异而非
   `__class__` 访问。
