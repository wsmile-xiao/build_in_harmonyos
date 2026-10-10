'use strict';
// 鸿蒙专属冒烟测试（真实 Leaflet 0.7.2 + jsdom 环境）
const assert = require('assert');
const path = require('path');
const Module = require('module');
const { JSDOM } = require('jsdom');

const geoJs = process.argv[2];
if (!geoJs) {
  console.error('Usage: node harmony_smoke.js <path-to-leaflet.geometryutil.js>');
  process.exit(1);
}

const dom = new JSDOM(
  '<!DOCTYPE html><html><body><div id="map" style="height:300px;width:400px"></div></body></html>',
  { pretendToBeVisual: true }
);

const define = (name, value) =>
  Object.defineProperty(global, name, { value, configurable: true, writable: true });

define('window', dom.window);
define('document', dom.window.document);
define('navigator', dom.window.navigator);
define('screen', dom.window.screen);
define('HTMLElement', dom.window.HTMLElement);
define('SVGElement', dom.window.SVGElement);

// jsdom 无 Canvas 2D context，补假对象
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

// SVG style 补可写对象
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

const L = require('leaflet');
const origLoad = Module._load;
Module._load = function (r, p, m) {
  if (r === 'leaflet') return L;
  return origLoad.apply(this, arguments);
};
require(path.resolve(geoJs));
Module._load = origLoad;

const G = L.GeometryUtil;
const latLng = L.latLng;
const point = L.point;
const map = L.map('map').fitWorld();

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log(`  ✓ ${name}`); pass++; }
  catch (e) { console.error(`  ✗ ${name}\n      ${e.message}`); fail++; }
}

console.log('=== HarmonyOS smoke test: leaflet-geometryutil 0.4.0 ===');

console.log('\n[1] API 挂载（鸿蒙专属）');
test('L.GeometryUtil 已挂载', () => assert.ok(G));
const apiList = [
  'distance','distanceSegment','readableDistance','belongsSegment',
  'length','accumulatedLengths','closestOnSegment','closest','closestLayer',
  'closestLayerSnap','interpolateOnPointSegment','interpolateOnLine','locateOnLine',
  'reverse','extract','isBefore','isAfter','startsAtExtremity','computeAngle',
  'computeSlope','rotatePoint','bearing','destination'
];
apiList.forEach(fn =>
  test(`L.GeometryUtil.${fn} 是函数`, () => assert.equal(typeof G[fn], 'function')));

console.log('\n[2] 纯函数数值（鸿蒙专属）');
test('computeAngle 45°', () => assert.equal(G.computeAngle(point(0,0), point(1,1)), 45));
test('computeAngle 0°', () => assert.equal(G.computeAngle(point(0,0), point(5,0)), 0));
test('computeSlope {a:2,b:0}', () => {
  const s = G.computeSlope(point(0,0), point(2,4));
  assert.equal(s.a, 2); assert.equal(s.b, 0);
});
test('interpolateOnPointSegment ratio=0.5', () => {
  const p = G.interpolateOnPointSegment(point(0,0), point(10,20), 0.5);
  assert.equal(p.x, 5); assert.equal(p.y, 10);
});
test('readableDistance metric <1km', () => assert.equal(G.readableDistance(500), '500 m'));
test('readableDistance metric >1km', () => assert.equal(G.readableDistance(1500), '1.50 km'));
test('readableDistance imperial', () => assert.equal(G.readableDistance(500, 'imperial'), '547 yd'));
test('length([]) === 0', () => assert.equal(G.length([]), 0));
test('accumulatedLengths([])', () => assert.deepEqual(G.accumulatedLengths([]), []));
test('bearing 正东 ≈ 90°', () => {
  const b = G.bearing(latLng(0,0), latLng(0,1));
  assert.ok(Math.abs(b - 90) < 0.01, `got ${b}`);
});
test('bearing 正北 ≈ 0°', () => {
  const b = G.bearing(latLng(0,0), latLng(1,0));
  assert.ok(Math.abs(b) < 0.01, `got ${b}`);
});
test('destination 零距离', () => {
  const p = G.destination(latLng(0,0), 0, 0);
  assert.ok(Math.abs(p.lat) < 1e-9 && Math.abs(p.lng) < 1e-9);
});
test('destination 正东 1000m', () => {
  const p = G.destination(latLng(0,0), 90, 1000);
  assert.ok(Math.abs(p.lat) < 1e-6);
  assert.ok(Math.abs(p.lng - 0.008983) < 0.001);
});

console.log('\n[3] 鸿蒙平台消费者场景');
test('消费者 require 包后 L.GeometryUtil 可用', () => {
  assert.ok(L.GeometryUtil);
  assert.equal(typeof L.GeometryUtil.interpolateOnLine, 'function');
});
test('地图实例上调用 distanceSegment', () => {
  const d = G.distanceSegment(map, latLng(0,0), latLng(0,-1), latLng(0,1));
  assert.ok(d < 1e-6);
});
test('地图实例上调用 closest', () => {
  const r = G.closest(map, [latLng(0,0), latLng(0,2)], latLng(1,1));
  assert.ok(r && typeof r.lat === 'number');
});

console.log(`\n=== Result: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);
