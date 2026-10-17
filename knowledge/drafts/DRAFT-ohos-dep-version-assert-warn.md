# DRAFT-ohos-dep-version-assert-warn — 上游依赖版本区间的硬断言只发告警时，不要盲目降级适配整条遗留依赖链

> Contributor: 9C75 / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-dep-version-assert-warn`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-VENDP-PUREPY-DEP-CLOSURE` | 草稿 | 制品仓 **无该依赖的任何配方** → vendor 进包内 site-packages | 本条与之相反：依赖在制品仓**有**（只是版本更新），冲突点是"上游写了窄版本区间"，不是"没有配方" |
| `E2176`（A7F3 草稿） | 草稿 | CI worker 缺第三方模块 → 显式 SKIP | E2176 是**运行时缺模块**；本条是**导入期版本断言告警**，且模块齐全、实际可用 |
| `E396` Conan 图身份与包物化 | 已收录 | Conan graph/package_folder 语义 | 无关（Conan 内部机制 vs 上游库自身版本检查） |

**全库查证**：对 `check_compatibility` / `doesn't match a supported` / `DependencyWarning` /
`版本区间` / `requirement.*range.*assert` 五项，在 `knowledge/index.tsv`、
`knowledge/graph/index.tsv`、`knowledge/graph/*.kv`、`knowledge/doc/*.md`、
`knowledge/drafts/*.kv`、`knowledge/drafts/*.md` 中 grep，**命中 0 条**。

## Scope（何时用）

上游 `requires_dist` 是**窄版本区间**，而制品仓只发布了**更新**版本，且上游对区间做了
硬断言（`assert`）。典型案例：requests 2.22.0。

| 依赖 | 上游 2.22.0 要求 | ohpcd 已发布 |
|---|---|---|
| certifi | >=2017.4.17 | 2026.7.22 |
| chardet | >=3.0.2,**<3.1.0** | 5.2.0 |
| idna | >=2.5,**<2.9** | 3.18 |
| urllib3 | >=1.21.1,**<1.26** | 2.7.0 |

## Symptom

```console
$ python3 -c "import requests"
.../requests/__init__.py:89: RequestsDependencyWarning:
    urllib3 (2.7.0) or chardet (5.2.0) doesn't match a supported version!
```

源码（`requests/__init__.py`，2.22.0）：

```python
def check_compatibility(urllib3_version, chardet_version):
    ...
    assert major == 1; assert minor >= 21; assert minor <= 25   # urllib3
    assert major == 3; assert minor < 1;  assert patch >= 2     # chardet
...
try:
    check_compatibility(urllib3.__version__, chardet.__version__)
except (AssertionError, ValueError):
    warnings.warn("urllib3 ({}) or chardet ({}) doesn't match a supported "
                  "version!".format(...), RequestsDependencyWarning)
```

## Root Cause

**该 `assert` 被 `try/except` 包住 → 只发 `warnings.warn`，不阻断任何代码路径。**
它表达的是"未经上游测试的组合"，不是"已知不可用"。因此真正的判据不是"告警存在"，
而是"**消费者实际调用路径是否仍然工作**"。

若不做实测就按字面降级，代价很重：需额外适配并发布 `urllib3/1.25.3`、`chardet/3.0.4`、
`idna/2.8` 三个遗留包，且按 W2（一个 PR 只允许一个软件目录）与 PF4（依赖闸）它们
必须**各自独立 PR**，不能与本包捎带——链路大幅拉长，收益存疑。

## Recommended Solution

### 主方案（priority 1）— `use-prebuilt-package`

采用制品仓已发布的新版依赖，用**实测**证明告警非致命，并在配方与 notes.md 写明
"该告警属预期"。requests 2.22.0 实测（Python 3.12.9 + ohpcd 版本组合）：

| 验证项 | 结果 |
|---|---|
| `import requests` | OK（伴随且仅伴随 1 条 `RequestsDependencyWarning`）|
| 真实 HTTPS GET（pypi.org）| **200**，响应体正常 |
| 重定向 / `allow_redirects` | OK |
| `HTTPAdapter(max_retries=Retry(...))` | OK |
| 超时传播（不可达地址）| 正确抛 `ConnectTimeout` |
| idna 非 ASCII 域名 | 正确转 punycode `xn--r8jz45g.xn--zckzah` |
| `requests.exceptions.*` 层次 | ConnectionError / ReadTimeout / SSLError / ProxyError / RetryError 齐全 |

配套做法：在 test_package 里**显式断言该告警存在且仅一条**——

```python
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    import requests
dep = [w for w in caught if issubclass(w.category, RequestsDependencyWarning)]
assert len(dep) == 1
```

这样将来行为变化（告警消失=上游行为变了，或新增告警=依赖不兼容）能被立刻发现。

### 回退方案（priority 2）— `adapt-legacy-dependency-chain`

**仅当实测发现新版确实在关键路径失败**（类型错误/行为变更/接口删除）时，才按拓扑序
先适配并发布遗留依赖，且各自独立 PR：

```bash
conan download "urllib3/1.25.3" -r=ohpcd --only-recipe   # 先确认是否已发布
```

### 禁止做法

- ❌ 在同一 PR 内新增 `archives/{u,c,i}/(urllib3|chardet|idna)/`——为"仅告警"的断言去适配整条遗留链，会被 CI JC6/PF1 直接拦截。
- ❌ 全局 `warnings.filterwarnings("ignore", ...)` 屏蔽告警——会掩盖将来真实的行为变更；应改为在消费者测试里显式断言。

## 单库实证

| 库 | 依赖策略 | 结果 |
|---|---|---|
| requests 2.22.0 | 采用 ohpcd 新版（certifi 2026.7.22 / chardet 5.2.0 / idna 3.18 / urllib3 2.7.0）| 实测全通过，仅 1 条预期告警；自足上游测试子集 36 passed / 1 skipped |

## 测试覆盖边界

本条只覆盖"**导入期版本区间断言**"这一形态。若上游是**运行期**做版本检查并 raise
（而非 warn），或新版依赖真的删除了被调用的接口，则不适用主方案，须走回退方案。

## 关联条目

- 相似：`E2176`（依赖缺失的 SKIP 边界）、`E396`（Conan 依赖物化）
- 差异：见上方差异化定位表
