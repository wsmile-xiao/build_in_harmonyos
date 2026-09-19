# DRAFT-ohos-markupsafe-soft-unicode-removal-dual-version-lines — soft_unicode 移除导致两条版本线并存

> Contributor: B7A4 / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 3 (high)
> Prospect ID: `DRAFT-ohos-markupsafe-soft-unicode-removal-dual-version-lines`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E241` | 图谱 | 依赖版本区间不满足（可选合适版本即可解）| 本条是**区间互斥**——不存在同时满足的单一版本，必须并存两条线 |
| `E305` | 图谱 | 同上族：版本约束不满足 | 同上；本条不是"选版本"问题而是"**必须并存**"问题 |
| — | — | — | 全库对 `soft_unicode` / `soft_str` 命中 **0 条** |

**全库查证**：对 `soft_unicode`、`soft_str`、`MarkupSafe 2.1`、`同包多版本并存`、
`Jinja2 2.10` 等关键词，在 `knowledge/index.tsv`、`knowledge/graph/index.tsv`、
`knowledge/graph/*.kv`、`knowledge/doc/*.md`、`knowledge/drafts/*.kv`、
`knowledge/drafts/*.md` 中 grep —— 除本条外**命中 0 条**（`MarkupSafe` 的 2 处命中
来自 `DRAFT-libfirm-1.22.0-python312-vendored-generators`，语境是 vendored 生成器，
与本条无关）。

## Scope（何时用）

同一制品仓（ohpcd）需**同时**服务新旧两条 Pallets 链：

| 消费链 | 典型起点 | 需要的 markupsafe |
|---|---|---|
| 旧链 | `requests` 2.22.0 → `Jinja2` 2.10.1 | **<= 2.0.1** |
| 新链 | `flask` 3.x → `Jinja2` 3.1.6 | **>= 2.1.1** |

## Symptom

旧链在新版 markupsafe 下 import 即失败：

```console
ImportError: cannot import name 'soft_unicode' from 'markupsafe'
```

## Root Cause

`soft_unicode` 是 MarkupSafe 1.x 的别名函数（等价 `str()`）：**2.0 标记废弃、
2.1 正式移除**。而 **Jinja2 2.10.x 的 `jinja2/utils.py` 里有
`from markupsafe import soft_unicode`** —— 于是形成版本死锁：

```
Jinja2 2.10.1  →  markupsafe <= 2.0.1
Jinja2 3.1.6   →  markupsafe >= 2.1.1
                  ↑ 区间互斥，无交集
```

> ⚠️ **易错点**：`soft_str` 与 `soft_unicode` 命运**不同**。实测 3.0.3 源码中
> `soft_unicode` 0 处命中（已移除），而 **`soft_str` 仍然存在**
> （`src/markupsafe/__init__.py:64`，且 `soft_str(None) == "None"` 可调用）。
> 把两者一起当作"已移除"会写出错误的消费者断言。

## Recommended Solution

### 主方案（priority 1）— 两条版本线并存发布

```
archives/m/markupsafe/1.1.1/   # 服务 Jinja2 2.10.1（旧链）
archives/m/markupsafe/3.0.3/   # 服务 Jinja2 3.1.x（新链）
```

- 各自 `conanfile` 的 `version`、分支名 `feat/markupsafe-<ver>`、版本目录
  **三者对齐**（L0n/R40）；
- 两边 `notes.md` 都写明**并存理由**与"**不可互相替代**"，防止后来者
  把它当重复配方删掉其一；
- 交付形态按纯 Python 包惯例：直接拷 `markupsafe/` 目录，不调用 PEP 517 构建。

**并按版本线差异化交付**（实测决定）：

| 版本 | 交付形态 | 理由 |
|---|---|---|
| 1.1.1 | 纯 Python（既有做法）| 上游 1.x 的 C 加速器非必需 |
| 3.0.3 | **只交付纯 Python 回退**（跳过 `_speedups.c`）| `__init__.py` 有 `try: from ._speedups import ... / except ImportError: from ._native import ...`，纯 Python 是上游**受支持**模式；塞 `.so` 会把构建机 CPython ABI/架构绑进 `python-require` 包 |

### 回退方案（priority 2）— 消费者侧打补丁

仅在**被迫收敛为单版本**时：把消费者的
`from markupsafe import soft_unicode` 改写为等效实现（`soft_unicode = str`）。
缺点：改动落在第三方源码上、每次升级重做、偏离上游兼容原则——**最后手段**，
且必须在 notes.md 记录该补丁与其脆弱性。

### 禁止做法

- ❌ 「升级到最新 markupsafe 即可统一」——区间互斥，会让旧链 ImportError；
- ❌ 断言 `soft_str` 与 `soft_unicode` 一起被移除——实测 `soft_str` 仍在。

## 实测证据（2026-09-16，markupsafe 3.0.3 适配）

| 项 | 结果 |
|---|---|
| 3.0.3 源码 `soft_unicode` | **0 处命中**（已移除）|
| 3.0.3 源码 `soft_str` | **存在**（`__init__.py:64`），`soft_str(None) == "None"` |
| 消费者测试 | 固化分界线：`not hasattr(markupsafe, "soft_unicode")` 且 `callable(markupsafe.soft_str)` |
| 并存关系 | ohpcd 侧 `markupsafe/1.1.1` 与 `markupsafe/3.0.3` 必须同时可用 |

## 测试覆盖边界

本条处理"**符号移除导致区间互斥**"。区分相邻情形：

- 单纯版本区间不满足（存在可行交集）→ `E241` / `E305`；
- 元数据双来源不一致（`setup.py` 与模块 `__version__` 不符）→
  `DRAFT-multipledispatch-version-metadata-reconciliation`。

## 关联条目

- 相似：`E241`、`E305`（版本区间不满足族，但可选版本解决）
- 差异：见上方差异化定位表
