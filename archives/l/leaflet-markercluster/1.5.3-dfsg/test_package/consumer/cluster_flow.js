'use strict';
// 完整消费者用例（端到端）：模拟真实 Web 应用集成 Leaflet.markercluster 的完整流程。
//
// 流程：模块加载 → 建图 → 批量添加 100 个真实标记 → 低缩放级聚合生效（1 个聚合
// 含全部标记）→ 放大到高缩放级 → 聚合解散、标记各自直接可见 → removeLayer 移除
// → 整组从地图摘除。
//
// 被测对象 = 包安装产物（argv[2]，share/leaflet-markercluster/leaflet.markercluster.js）。
// 运行时 = 真实 Leaflet 1.9.4（./leaflet.min.js，消费方 Web 应用提供的依赖，
// BSD-2-Clause），运行环境 = Node + 最小 DOM 桩（./dom-shim.js）。
// 全部断言走公共 API（markerClusterGroup / addLayers / getVisibleParent /
// getChildCount / hasLayer / removeLayer / setView / hasLayer(map)），
// 中间断言只是验证节点，整体是一个真正跑通功能/流程的可执行消费者程序。
//
// 用法：node cluster_flow.js <packaged leaflet.markercluster.js>

const fs = require('fs');

const distPath = process.argv[2];
if (!distPath || !fs.existsSync(distPath)) {
    console.error('usage: node cluster_flow.js <packaged leaflet.markercluster.js>');
    process.exit(2);
}

require('./dom-shim.js'); // Node 无浏览器 DOM：注入 Leaflet 渲染管线所需最小桩

// 真实 Leaflet 1.9.4。require() 走 UMD 的 exports 分支 → L 由本模块导出；
// 被测插件 UMD 的浏览器分支引用全局 L，故补设全局 L（等价于浏览器 <script> 加载后的状态）。
const L = require('./leaflet.min.js');
global.L = L;

// 以浏览器 <script> 语义加载被测包产物（new Function 中 exports/define 均未定义，
// UMD 走浏览器分支，把 L.MarkerClusterGroup 挂到现有全局 L 上）。
new Function(fs.readFileSync(distPath, 'utf8'))();

let pass = 0;
let fail = 0;
function check(name, cond) {
    if (cond) {
        pass += 1;
        console.log('  [ok] ' + name);
    } else {
        fail += 1;
        console.log('  [FAIL] ' + name);
    }
}

// ---------- 1) 模块加载：插件在真实 Leaflet 环境下成功挂载 ----------
check('markerClusterGroup factory mounted on L', typeof L.markerClusterGroup === 'function');
check('MarkerClusterGroup class exported', typeof L.MarkerClusterGroup === 'function');

// ---------- 2) 建图（真实 Leaflet 地图，视口 800×600，zoom 0 世界级） ----------
const container = document.createElement('div');
const map = L.map(container, {
    zoomControl: false,
    attributionControl: false,
    minZoom: 0,
    maxZoom: 18, // 上游 onAdd 要求地图声明 maxZoom（真实 Web 应用通过底图/选项提供，此处同款）
    renderer: L.svg(), // 真实应用必有矢量渲染器（polyline/marker 侧需要），onAdd 的 spiderfier 初始化会查它
}).setView([20, 0], 0);
check('map created at z0', map.getZoom() === 0);

// ---------- 3) 创建聚合组并挂到地图 ----------
// removeOutsideVisibleBounds:false 为公共选项（消费方自行管理裁剪的应用标准用法），
// 让本用例对全部 100 个标记做确定性的解散验证，不依赖视口内外的运气。
const group = L.markerClusterGroup({
    animate: false,
    animateAddingMarkers: false,
    showCoverageOnHover: false,
    zoomToBoundsOnClick: false,
    spiderfyOnMaxZoom: false, // 本用例验证聚合/解散核心流程，不触发 spiderfy
    removeOutsideVisibleBounds: false,
});
map.addLayer(group);
check('group on map', map.hasLayer(group));

// ---------- 4) 批量添加 100 个真实标记（10×10 网格、格距 0.5°，约 5°×5°：
//              z0 时全部落入同一聚合半径（世界仅 256px，5°≈3.5px）→ 必然聚成
//              1 个聚合；z15 时相邻标记像素距 ≈1 万 px，远大于聚合半径 → 必然
//              全部散开。±0.02° 抖动避免坐标完全重合） ----------
const markers = [];
for (let i = 0; i < 100; i++) {
    const lat = -2.25 + (i % 10) * 0.5 + (i % 5) * 0.02;
    const lng = -2.25 + Math.floor(i / 10) * 0.5 + (i % 3) * 0.02;
    markers.push(L.marker([lat, lng]));
}
group.addLayers(markers);
check('100 markers accepted by group', group.getLayers().length === 100);
check('every marker registered via hasLayer', markers.every((m) => group.hasLayer(m)));

// ---------- 5) 低缩放级聚合生效：可见父级是聚合对象且含全部 100 个标记 ----------
const parent = group.getVisibleParent(markers[0]);
check('at z0 marker is clustered (visible parent is a cluster)', !!parent && parent !== markers[0]);
check('cluster child count == 100', !!parent && parent.getChildCount() === 100);
check('cluster icon actually rendered on map pane', !!parent && !!parent._icon); // _icon 仅作观察

// ---------- 6) 放大到 z15：聚合解散，标记各自直接可见 ----------
// z15 下相邻标记像素距（0.5°≈1.1 万 px）远大于聚合半径 → 全部散开。
map.setView([0, 0], 15, { animate: false });
check('de-clustered at z15 (visible parent is the marker itself)',
      group.getVisibleParent(markers[0]) === markers[0]);
let visibleCount = 0;
for (const m of markers) {
    if (group.getVisibleParent(m) === m) { visibleCount += 1; }
}
check('all 100 markers individually visible at z15', visibleCount === 100);

// ---------- 7) 移除流程（真实应用中删点/整组摘除的日常操作） ----------
group.removeLayer(markers[0]);
check('removeLayer drops marker from group', !group.hasLayer(markers[0]));
check('group size 99 after removal', group.getLayers().length === 99);

// ---------- 8) 收尾：整组从地图移除 ----------
map.removeLayer(group);
check('group removed from map', !map.hasLayer(group));

console.log('=== Consumer E2E: ' + pass + ' passed, ' + fail + ' failed ===');
process.exit(fail ? 1 : 0);
