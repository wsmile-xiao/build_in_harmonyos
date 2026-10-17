# DRAFT: mapbox 依赖族版本锁定 vs 制品仓新版本 API 差异

- **草稿 ID**: DRAFT-geojson-vt-cpp-6.6.5-mapbox-dep-family-version-lock-api-drift
- **来源库**: geojson-vt-cpp 6.6.5（mapbox/geojson-vt-cpp，header-only C++14，OHOS armv8 适配）
- **状态**: 草稿（待审核提升为正式条目）
- **日期**: 2026-09-27

## 问题

上游 geojson-vt-cpp 6.6.5 的 Makefile（春mason 依赖体系）锁定依赖版本：
`variant 1.1.5 / geometry 1.0.0 / geojson-cpp 0.4.3 / gtest 1.8.0 / rapidjson 1.1.0 / benchmark 1.4.1`。

制品仓（ohpcd）已发布新版本：`mapbox-variant/1.2.0` 与 `mapbox-geometry/2.0.3`。

用制品仓新版本直接编译**上游测试套件**时失败：

```
variant.hpp:332:20: error: no matching function for call to object of type 'mapbox::geojson::to_value'
    return std::forward<F>(f)(unwrapper<T>::template apply<V>(v));
```

即 variant 1.2.0 的 `visit/apply` 内部 `dispatcher::apply` 模板解析方式变化后，
旧 geojson-cpp 0.4.3 的 `mapbox::geojson::to_value` 访问器（对 `null_value_t/bool/unsigned long/...`
的 `operator()` 重载集）无法匹配。

关键点：库**公共 API**（`mapbox::geojsonvt::geoJSONToTile / GeoJSONVT / Tile`）与依赖版本
无关——用制品仓版本组合编译冒烟通过；差异仅在**上游测试源码 × 旧访问器 × 新 variant** 组合层。

## 根因

1. 上游构建脚本锁定旧依赖版本（mason 体系）；
2. 制品仓发布的新版本依赖内部 API（visit/dispatcher 模板解析）发生了变化；
3. 上游测试源码对依赖包的内部 API 存在版本耦合（`to_value` 访问器重载集）。

## 方案

**双版本口径分离**：

| 口径 | 依赖版本 | 用途 |
|------|----------|------|
| 上游测试套件 | variant 1.1.5 + geometry 1.0.0 + geojson-cpp 0.4.3 + rapidjson 1.1.0 + gtest 1.17.0 | 忠实运行上游测试，计算全量通过率 |
| 库配方 requirements | mapbox-variant/1.2.0 + mapbox-geometry/2.0.3（制品仓已发布） | 配方可发布、下游可解析 |
| 消费者编译冒烟 | 制品仓版本组合 | 验证"配方依赖 × 库公共 API"兼容 |

消费者冒烟仅使用公开 API（`<mapbox/geojsonvt.hpp>`），例如：
`geoJSONToTile(point) → 1 feature`、`linestring → int16 量化线段`、
`GeoJSONVT.getTile lineMetrics clip_start≈0.660622`。

## 验证

- 上游测试（锁定版本组合）: 23/23 PASS（100%）
- conan-verify: G1-G4/L2/L4/L5 全绿
- 消费者 test_consumer（制品仓版本组合）: C1/C3 PASS
- W3 本地 CI: L0=pass（prdiff 单包口径），Pass rate 100%

## 适用边界

- **适用**: 依赖 mapbox variant/geometry/geojson 依赖族的 header-only/header-heavy 库；
  以及任何"上游测试对依赖包内部 API 有版本耦合"的三方库。
- **反例**: 依赖族无 API 变化、或上游测试不直接触碰依赖内部 API 时，无需版本锁定分离。

## 查重

四范围（正式知识/图谱/草稿）未命中或仅部分覆盖：

| 轴 | 结果 | 说明 |
|----|------|------|
| exact_duplicate | false | 无条目描述 mapbox 依赖族版本锁定 + API 差异 |
| causal_duplicate | false | 无同根因条目 |
| trigger_overlap | 部分 | E1000-draft 提及 mapbox-variant consumer + 上游测试隔离，未覆盖版本组合锁定模式 |
| solution_overlap | 部分 | "上游测试可独立运行"有提及，无完整处方 |
| combination_novelty | true | variant 1.2.0 dispatcher × geojson-cpp 0.4.3 to_value 组合差异 |
| boundary_novelty | true | 适用边界（mapbox 依赖族）+ 反例明确 |
| test_migration_novelty | true | 测试运行口径与配方消费口径分离 |

**关系**: similar_to E1000-draft / E321 / E322；无 prerequisite_of / conflicts_with。

## 决策

路径 B（知识库扩展）→ **new_draft**