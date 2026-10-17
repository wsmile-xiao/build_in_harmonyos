# DRAFT-ohos-source-copy-python-no-dist-info-version-unavailable — 源码直拷无 .dist-info，惰性 __version__ 不可用

> Contributor: C1D9 / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-source-copy-python-no-dist-info-version-unavailable`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-multipledispatch-version-metadata-reconciliation` | 草稿 | **两个元数据来源互相不一致**（`setup.py`/PyPI metadata 与模块 `__version__` 各说各话，需双来源校验）| 那是"元数据**存在但矛盾**"；**本条是"元数据的来源压根不存在"**——`.dist-info` 未随包交付，`importlib.metadata` 抛 `PackageNotFoundError`。实测该草稿全文不含 `dist-info` / `PackageNotFoundError` 判据 |
| — | — | — | 全库对 `dist-info` / `PackageNotFoundError` 命中 **0 条**（`importlib.metadata` 仅 2 处命中，均在上述 multipledispatch 草稿）|

**全库查证**：对 `importlib.metadata`、`dist-info`、`PackageNotFoundError`、
`源码直拷` 等关键词，在 `knowledge/index.tsv`、`knowledge/graph/index.tsv`、
`knowledge/graph/*.kv`、`knowledge/doc/*.md`、`knowledge/drafts/*.kv`、
`knowledge/drafts/*.md` 中 grep —— 除上表（语境不同）外**命中 0 条**。

## Scope（何时用）

**所有采用"源码直拷"交付的 Python 包**（本仓全部 Python 包均如此：只把可导入的
包目录拷进 `site-packages`），且该包的 `__version__` 走 `importlib.metadata`。

典型是 **Pallets 系**：`itsdangerous` / `markupsafe` / `werkzeug` / `click` / `flask`。

## Symptom

`import` 成功、**其余 API 全部正常**，**只有** `__version__` 失败：

```console
$ python3 -c "import itsdangerous; print(itsdangerous.__version__)"
PackageNotFoundError: No package metadata was found for itsdangerous
```

> ⚠️ **易误判点**：功能一切正常而仅版本号取不到，容易被误诊为"包坏了 / 装错了 /
> 打包失误"，从而走向重建、重装等无效方向。

## Root Cause

Pallets 系用模块级 `__getattr__` **惰性**解析 `__version__`：

```python
# itsdangerous/__init__.py（节选）
def __getattr__(name: str) -> t.Any:
    if name == "__version__":
        import importlib.metadata
        warnings.warn("The '__version__' attribute is deprecated ...",
                      DeprecationWarning)
        return importlib.metadata.version("itsdangerous")
    raise AttributeError(name)
```

`importlib.metadata.version()` 会**遍历 `sys.path` 查找 `<包名>-*.dist-info` 目录**。

而本仓 Python 包的 `package()` 只拷贝可导入的包目录：

```
lib/python3.12/site-packages/itsdangerous/     ← 交付
lib/python3.12/site-packages/itsdangerous-2.2.0.dist-info/   ← 不交付（wheel 产物）
```

**因此这是打包形态的必然结果，不是 API 缺陷**：`.dist-info` 属 wheel **安装**产物，
源码直拷模式本就不带。

## Recommended Solution

### 主方案（priority 1）— 消费者测试避开 `__version__`，改断言功能 API

`__version__` 属**安装形态相关**的元数据，**不是**该包承诺的 API 契约。正确口径是
断言真实行为：

```python
# ✅ 功能断言（稳定、且真正验证交付物可用）
assert signer.unsign(signer.sign("v")) == b"v"

# ❌ 避免（依赖安装形态）
assert itsdangerous.__version__ == "2.2.0"
```

并在测试注释里写明**为何**不断言 `__version__`——防止后来者"好心补上"这个断言
又踩同一个坑。

**若某包的 `__version__` 恰好可用**（如 markupsafe 3.0.3 走弃用告警路径仍能取到），
也应用 `warnings.catch_warnings()` 静默其 `DeprecationWarning`，避免污染测试输出。

### 回退方案（priority 2）— 随包生成 `.dist-info`

若**确实**需要 `importlib.metadata.version()` 可用（例如消费者框架强依赖它），
可在 `package()` 内额外生成最简 `<name>-<ver>.dist-info/METADATA` 一并交付。
代价是引入"手工维护的元数据"，**必须与上游保持一致并随版本同步**——属可选增强，
非默认做法。

### 禁止做法

- ❌ 手工伪造 `.dist-info` 却不同步校验——会制造"元数据撒谎"，比缺失更糟
  （消费者据错误版本做兼容判断）；
- ❌ 因 `PackageNotFoundError` 判定包损坏并反复重建——`import` 与全部功能 API
  均正常，重建不会改变结果。

## 实测证据（2026-09-16，itsdangerous 2.2.0 适配）

| 项 | 结果 |
|---|---|
| 触发点 | `itsdangerous/__init__.py` 的 `__getattr__` 经 `importlib.metadata.version()` 解析 `__version__` |
| 症状 | 仅 `__version__` 抛 `PackageNotFoundError`；其余 API（签名/序列化/编码助手）全部正常 |
| 交付形态 | 只拷 `itsdangerous/` 目录（8 个文件），不含 `.dist-info` |
| 处置 | 消费者测试**刻意不断言** `__version__`，改为 7 组功能断言；测试注释说明理由 |
| 对照 | markupsafe 3.0.3 的 `__version__` 仍可用但走弃用告警 → 用 `warnings.catch_warnings()` 静默 |
| 上游 pytest | 297 passed（不涉及本节问题）|

## 测试覆盖边界

本条处理"**元数据来源不存在**"。区分相邻情形：

- 元数据**双来源互相矛盾**（`setup.py` vs 模块 `__version__`）→
  `DRAFT-multipledispatch-version-metadata-reconciliation`；
- 版本区间不满足 → `E241` / `E305`。

## 关联条目

- 相似：`DRAFT-multipledispatch-version-metadata-reconciliation`（元数据不一致）
- 差异：见上方差异化定位表
