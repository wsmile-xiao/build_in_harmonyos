# 完整消费者用例（端到端）

`cluster_flow.js` 是 rule12（鸿蒙特有测试须含完整消费者用例）要求的端到端用例：
以真实消费方 Web 应用的方式集成被测包产物，跑通完整功能流程。

```
node --jitless cluster_flow.js <share/leaflet-markercluster/leaflet.markercluster.js>
```

## 运行方式

- **运行时**：真实 Leaflet 1.9.4（`leaflet.min.js`，见下）。markercluster 是 Leaflet
  插件，必须在 Leaflet 之后加载——本用例与真实 Web 应用同构：先加载 Leaflet，
  再以浏览器 `<script>` 语义加载被测包产物（UMD 浏览器分支挂载到全局 `L`）。
- **DOM**：Node 无浏览器环境，`dom-shim.js` 提供 Leaflet 渲染管线所需的最小 DOM
  桩（createElement/appendChild/style/classList 等）。聚合算法（DistanceGrid、簇树、
  缩放合并/分裂）全部是纯 JS 计算，与桩无关；桩只承接渲染胶水。
- **OHOS**：设备 node 的 V8 JIT 直接 SIGTRAP，须 `--jitless`（知识库 E400）。

## 流程（14 个验证节点，全部走公共 API）

1. 模块加载：`L.markerClusterGroup` 工厂挂载成功
2. 建图（真实 Leaflet 地图，800×600 视口，z0）
3. 聚合组挂图（`map.addLayer(group)`）
4. 批量添加 100 个真实标记（10×10 网格、格距 0.5°）
5. z0 聚合生效：可见父级是聚合对象、childCount=100（1 簇含全部标记）、簇图标已渲染
6. 放大 z15：聚合解散，100 个标记各自直接可见（`getVisibleParent(m) === m`）
7. `removeLayer` 移除单标记、`hasLayer` 反映
8. 整组从地图摘除

选项说明（均为公共 API，真实应用常规用法）：
- `removeOutsideVisibleBounds: false`：消费方自行管理裁剪的应用标准用法；让本用例
  对全部 100 个标记做确定性解散验证，不依赖视口内外运气。
- `animate: false` / `animateAddingMarkers: false`：无浏览器动画环境，走同步管线。
- `spiderfyOnMaxZoom: false`：本用例验证聚合/解散核心流程，不触发 spiderfy。
- `renderer: L.svg()`：真实应用必有矢量渲染器（polyline 侧需要）。

## 随档文件

| 文件 | 说明 |
|------|------|
| `leaflet.min.js` | Leaflet 1.9.4 官方 npm 发行物 `dist/leaflet.js`（minified UMD），
仅作测试夹具（消费方应用提供的运行时依赖），不进入包产物。sha256:
`db49d009c841f5ca34a888c96511ae936fd9f5533e90d8b2c4d57596f4e5641a`，
许可 BSD-2-Clause（Copyright (c) 2010-2024 Volodymyr Agafonkin）。 |
| `dom-shim.js` | 最小 DOM 桩（仅测试环境胶水） |
| `cluster_flow.js` | 消费者端到端用例本体 |
