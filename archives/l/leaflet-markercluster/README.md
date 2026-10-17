# Leaflet.markercluster

Leaflet 地图标记聚合插件：把地图上密集的标记点聚合成可展开的聚合簇（MarkerClusterGroup），
是大规模点数据可视化的标准前端组件。

## 功能概述

- `L.MarkerClusterGroup`：聚合/展开标记（含缩放动画、蜘蛛化展开 spiderfy）
- 聚合簇图标按规模分级（small/medium/large，纯 CSS 绘制，无图片资源）
- 支持 addLayers/removeLayers、按缩放级别禁用聚合、自定义聚合半径等

## OHOS 适配

- 纯 JS/CSS **资产包**：无编译步骤（上游 dist/ 即为运行时产物），配方只做安装布局与完整性校验
- 鸿蒙 PC 场景为浏览器 Web 应用提供本地静态资源（配合 Leaflet 本体使用）
- 与 Linux 无差异；测试策略：资产完整性断言 + 内容锚点（无浏览器环境可执行的测试）

## 依赖关系

- **运行时依赖**：Leaflet 1.x（本包为插件，JS 需在 Leaflet 之后加载；制品仓暂无 leaflet，
  由消费方 Web 应用自行提供）
- 编译依赖：无

## 参考资料

- 官网/仓库：https://github.com/Leaflet/Leaflet.markercluster
- npm：https://www.npmjs.com/package/leaflet.markercluster
