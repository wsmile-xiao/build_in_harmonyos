# DRAFT-ohos-gi-annotations-require-180 — glib:sync-func/async-func/finish-func 注解需 gobject-introspection ≥ 1.80

> Contributor: ohpcd / AtomCode | Status: DRAFT | Updated: 2026-09-18 | Severity: 🟠 major
> Source: gobject-introspection 1.80.1（PR #10682）——1.78.1.1 无法生成可用 introspection 数据的根因

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|----------|---------|--------|--------------------------|
| E429 | 已收录 | 消费者视角：OHOS 制品仓/系统镜像**无 .typelib**，运行时 `gi_repository_require` 必然报 `Typelib file for namespace 'GLib' not found`；根因是 glib2/2.88.0 以 introspection=disabled 构建 | 本 skill 是**上游能力缺口**：即使 typelib 存在，1.78.x 的 g-ir-scanner 生成的 GIR 中 Gio 异步方法 `is_async` 恒 FALSE（`glib:sync-func/async-func/finish-func` 注解 1.80.0 才引入，glib girparser 无 `_async` 后缀兜底）。E429 是「运行时没有 typelib」，本 skill 是「typelib 语义错误」——两层叠加时先修本 skill（换 1.80+）再谈 E429 |
| E430 | 已收录 | 消费者依赖图：消费 GI 必须对齐 glib2/2.88.0，混用 glib/2.84.x 触发 zlib 版本冲突 | 本 skill 与依赖版本无关，是 GI 自身 1.78 vs 1.80 的能力差异；E430 是「能不能装上」，本 skill 是「装上了能不能产出正确 GIR」 |
| E107 / E212 | 已收录 | 平台限制：Python 扩展模块 dlopen / loader 白名单 | 本 skill 与 dlopen 无关，是注解解析层面的功能缺陷；即使绕过 E107/E212 能跑 g-ir-scanner，1.78 产出的 is_async 依然错误 |

**撞车判定**：全库查证 `sync-func`（0 命中）、`uninstalled_gir_files`（0 命中）。E429/E430 均为消费者视角，未覆盖「GI 1.78 注解缺失导致 GIR 语义退化」这一上游能力缺口，作为独立条目申报。

## Scope（何时用）

- 需要 g-ir-scanner **现场生成 GIR/typelib** 的消费方（glib `-Dintrospection=enabled`、pygobject 上游测试等）
- 场景报错：`gi_callable_info_is_async(...) should be TRUE` / callable-info SIGABRT / Gio async 方法在绑定中全部表现为同步
- 正在评估 gobject-introspection 1.78.x 是否够用时

## Symptom

```
# glib 自身测试（1.78.x 生成的 GIR 下）
girepository+core/callable-info  → SIGABRT
# 报错
gi_callable_info_is_async(...) should be TRUE

# 语义级（不报错但静默错误）
Gio 的 279 个异步方法 is_async 恒为 FALSE
```

## Root Cause

1. `glib:sync-func` / `glib:async-func` / `glib:finish-func` 三个 GIR 注解是 **1.80.0 引入**（上游 NEWS：「Add annotations for sync, async, and async-finish functions in the GIR」）。
2. glib 的 `girparser.c` **只认这三个显式属性**，没有按函数名 `_async` 后缀推断 `is_async` 的兜底逻辑。
3. 因此 1.78.x 生成的 GIR 中 Gio 异步方法全部退化为同步语义；此问题**与库形态（共享/静态）无关**，是功能性硬缺陷。

源码对照（实测）：1.78 的 `girparser.py`/`girwriter.py`/`annotationparser.py` 对三注解命中数为 0/0/0；1.80.1 为 2/2/3。对 1.80.1 交付包内 girparser 实测：`async_func`/`sync_func`/`finish_func` 三个属性均正确解析。

## Workaround / 修复

- **正解**：适配 gobject-introspection **≥ 1.80.0**（本 skill 出处 PR #10682 即 1.80.1）。
- 不要「放松版本闸」硬跑 1.78 生成 typelib：产出 is_async 退化的 GIR 属掩盖而非适配。
- 对照验证：同一 GIR 输入分别喂 1.78 与 1.80 的 girparser，1.78 三属性全丢、1.80 全保留。

## Prevention

- 提 GI 相关 PR 前先查 ohpcd / main 现有版本；需要 introspection 的消费方直接要求 GI ≥ 1.80。
- 申报口径：上游用例数（`def test_` 函数数）与执行项数（pytest 参数化展开）勿混用。

## References

- PR #10682（GI 1.80.1 适配）
- gobject-introspection NEWS 1.80.0
- glib !3746（GIR 注解引入）
