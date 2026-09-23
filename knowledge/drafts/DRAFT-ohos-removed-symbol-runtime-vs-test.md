# DRAFT-ohos-removed-symbol-runtime-vs-test — 上游引用依赖中已被移除的符号：运行时须 pin，测试侧只需可选导入

> Contributor: 1428 / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-removed-symbol-runtime-vs-test`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-ohos-dep-version-assert-warn`（同批） | 草稿 | 上游对依赖做**版本区间硬断言**（`assert` 被 try/except 包住 → 仅告警）| 那条是"版本不匹配但符号都在，只警告"；本条是"符号**真的没了**，必须处理"。判据不同：前者看告警是否 gate 行为，本条看符号出现在**运行时还是测试侧** |
| `DRAFT-VENDP-PUREPY-DEP-CLOSURE` | 草稿 | 制品仓**无该依赖任何配方** → vendor 进包内 | 本条依赖在制品仓**有**（版本问题，非缺失问题）|
| `DRAFT-ohos-collections-abc-silent-loss`（同批） | 草稿 | `collections` 旧别名迁移 | 同属"符号被移除"大类，但符号族与判定维度不同：那条按**分支优先级**判定是否需补丁；本条按**引用位置**（运行时/测试侧）决定处置方式 |

**全库查证**：对 `soft_unicode` / `MarkupSafe 2.1` / `SNIMissingWarning` / `urllib3 2.x` /
`符号被移除` / `运行时 vs 测试侧` 等关键词，在 `knowledge/index.tsv`、`knowledge/graph/index.tsv`、
`knowledge/graph/*.kv`、`knowledge/doc/*.md`、`knowledge/drafts/*.kv`、`knowledge/drafts/*.md`
中 grep，**命中 0 条**。

## Scope（何时用）

上游库引用了依赖包在后续版本中**被移除的符号**，报错形态统一为
`ImportError: cannot import name X`。此时**必须先定位引用位置，再决定处置**。

本批两个方向的实例（同一错误形态、相反正确处置）：

| 库 | 引用位置 | 被移除符号 | 影响面 | 正确处置 |
|---|---|---|---|---|
| jinja2 2.10.1 | `jinja2/utils.py:647`（**运行时**）| `markupsafe.soft_unicode`（MarkupSafe 2.1 移除）| 消费者 import jinja2 即崩 | **pin markupsafe 1.1.1** |
| requests 2.22.0 | `tests/__init__.py:8`（**仅测试**）| `urllib3.exceptions.SNIMissingWarning`（urllib3 2.x 移除）| 交付产物零影响 | **改可选导入** |

## Symptom

同一形态，两种场景：

```console
# 运行时引用 → 消费者 import 直接失败
>>> import jinja2
ImportError: cannot import name 'soft_unicode' from 'markupsafe'

# 仅测试引用 → 交付产物可用，只有测试套件进不去
$ python3 -m pytest tests
tests/__init__.py:8: in <module>
    from urllib3.exceptions import SNIMissingWarning
ImportError: cannot import name 'SNIMissingWarning' from 'urllib3.exceptions'
```

## Root Cause

依赖包会在大版本升级中**移除**符号；上游库若仍引用它，就会在不同位置产生同一报错，
而两条处置路径的**代价与正确性完全相反**：

- **运行时导入**（包内 `.py` 顶层/核心模块）：该符号是**可交付契约**的一部分。
  忽略它 = 交付一个消费者无法 import 的包。若制品仓只有新版，就得专门适配兼容旧版
  （jinja2 2.10.1 → 必须适配 markupsafe 1.1.1）。
- **仅测试/构建期导入**（`tests/`、构建脚本）：与交付产物**无关**。此时若为它去降级
  运行时依赖，等于用测试需求去收缩生产依赖范围——既拉长依赖链，又与 W2
  （一 PR 一包）/ PF4（禁止捎带依赖）冲突。

## Recommended Solution

### 主方案（priority 1）— `classify-then-fix`

**第一步永远是定位引用位置**：

```bash
grep -rn "<被移除的符号>" <pkg>/        # 是否出现在交付的包目录（非 tests/、非构建脚本）
python3 -c "import <pkg>"              # 运行时导入则会直接失败
```

**分支 A：运行时引用 → pin 兼容版本**

```python
def requirements(self):
    # PyPI requires_dist: MarkupSafe>=0.23. Pinned to 1.1.1 because
    # jinja2/utils.py imports soft_unicode (gone in MarkupSafe 2.1).
    self.requires("markupsafe/1.1.1")
```

在 `requirements()` 相邻处**写明为何是非最新版本**，否则后人会"顺手升级"而破坏它。
配套：在 test_package 里断言该符号可用，把契约固化。

**分支 B：仅测试引用 → 可选导入**

```python
import urllib3
try:
    from urllib3.exceptions import SNIMissingWarning
except ImportError:  # urllib3 >= 2.0 removed SNIMissingWarning
    SNIMissingWarning = None
...
if SNIMissingWarning is not None:
    warnings.simplefilter('always', SNIMissingWarning)
```

**交付产物零改动**，并在 PR 描述注明"该补丁纯测试侧"（便于评审快速核验）。
验证方式：`grep -rn "<符号>" <pkg>/` 在运行时包目录应**零命中**。

### 回退方案（priority 2）— `source-patch`

若符号处于运行时路径、又确实无法 pin 旧版（制品仓无该版本且不便新适配），
只能在包内提供兼容 shim（同语义降级实现），并在 `notes.md` 记录语义差异。
此为本条**下策**，须在 PR 说明为何无法 pin。

### 禁止做法

- ❌ 因 `tests/` 里的 ImportError 去降级运行时依赖 → 为测试需求收缩生产依赖，且违反 W2/PF4。
- ❌ 把运行时包的符号改为可选导入 → 消费方静默得到与上游不同的行为，属隐瞒而非修复。

## 单库实证（2026-09-16）

| 库 | 分支 | 处置 | 结果 |
|---|---|---|---|
| jinja2 2.10.1 | A（运行时）| pin `markupsafe/1.1.1` | import 成功；上游测试 **533 passed, 2 failed, 1 error, 3 skipped**；test_package 断言 `soft_unicode` 契约通过 |
| requests 2.22.0 | B（测试侧）| `try/except` 可选导入补丁 | `grep -rn SNIMissingWarning requests/` **零命中**（纯测试侧）；上游自足子集 **36 passed, 1 skipped** |

## 测试覆盖边界

本条只覆盖"依赖包**移除**符号"这一形态。若依赖包只是**改了签名/行为**（符号仍存在），
则 import 不会失败，需靠行为测试发现——不属本条（参见 `DRAFT-ohos-dep-version-assert-warn`）。

## 关联条目

- 相似：`DRAFT-ohos-dep-version-assert-warn`（版本区间硬断言仅告警）、`DRAFT-ohos-collections-abc-silent-loss`（collections 旧别名）
- 差异：见上方差异化定位表
