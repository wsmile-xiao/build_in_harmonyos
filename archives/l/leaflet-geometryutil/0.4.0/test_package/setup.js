// 测试环境初始化：jsdom + 真实 Leaflet 0.7.2 + leaflet-geometryutil
const { JSDOM } = require('jsdom');
const Module = require('module');
const path = require('path');

const geoJs = process.env.GEO_JS;
if (!geoJs) {
  console.error('GEO_JS env var required');
  process.exit(1);
}

const dom = new JSDOM(
  '<!DOCTYPE html><html><body><div id="map" style="height:300px;width:400px"></div></body></html>',
  { pretendToBeVisual: true }
);
global.window = dom.window;
global.document = dom.window.document;
global.navigator = dom.window.navigator;
global.screen = dom.window.screen;
global.HTMLElement = dom.window.HTMLElement;
global.SVGElement = dom.window.SVGElement;

// jsdom 无 Canvas 2D context，补一个假对象让 Leaflet canvas 分支不崩
// 几何计算不依赖真实渲染，假 context 只承担属性读写
const makeFakeCtx = () => {
  const store = {};
  return new Proxy(store, {
    get: (t, k) => (k in t ? t[k] : (t[k] = () => {})),
    set: (t, k, v) => { t[k] = v; return true; }
  });
};
dom.window.HTMLCanvasElement.prototype.getContext = function () {
  if (!this.__fakeCtx) {
    Object.defineProperty(this, '__fakeCtx', { value: makeFakeCtx() });
  }
  return this.__fakeCtx;
};

// 给 SVGElement 补可写 style
const fakeStyle = () => new Proxy({}, {
  get: (t, k) => (k in t ? t[k] : ''),
  set: (t, k, v) => { t[k] = v; return true; }
});
Object.defineProperty(dom.window.SVGElement.prototype, 'style', {
  get() {
    if (!this.__fakeStyle) {
      Object.defineProperty(this, '__fakeStyle', { value: fakeStyle() });
    }
    return this.__fakeStyle;
  },
  configurable: true
});

// 加载真实 Leaflet 0.7.2
const L = require('leaflet');
global.L = L;

// hook require('leaflet')，让 geometryutil 的 UMD 拿到同一个 L 实例
const origLoad = Module._load;
Module._load = function (request, parent, isMain) {
  if (request === 'leaflet') return L;
  return origLoad.apply(this, arguments);
};
require(path.resolve(geoJs));
Module._load = origLoad;

// 上游 index.html 里的全局变量
global.map = L.map('map').fitWorld();
global.chai = require('chai');
