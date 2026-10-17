'use strict';
// 最小浏览器环境桩（Node 下运行 Leaflet 渲染管线所需的最小面）。
// 只提供 Leaflet 1.x 地图/图层/图标管线会触达的 DOM 接口，不含布局引擎：
// 聚合算法（DistanceGrid / 簇树 / 缩放合并分裂）全部是纯 JS 计算，
// 与桩无关；桩只承接 createElement/appendChild/style 等渲染胶水。
// 容器尺寸按 800×600 视口提供（getSize/getPixelBounds 依赖 clientWidth/Height）。

class StubClassList {
    constructor(el) { this._el = el; }
    add() {}
    remove() {}
    contains() { return false; }
    toggle() { return false; }
}

function makeEl(tag) {
    return {
        tagName: String(tag).toUpperCase(),
        style: {},
        className: '',
        classList: new StubClassList(),
        children: [],
        parentNode: null,
        attributes: {},
        clientWidth: 800,
        clientHeight: 600,
        offsetWidth: 800,
        appendChild(c) { c.parentNode = this; this.children.push(c); return c; },
        removeChild(c) {
            const i = this.children.indexOf(c);
            if (i >= 0) { this.children.splice(i, 1); }
            c.parentNode = null;
            return c;
        },
        insertBefore(c, ref) { return this.appendChild(c); },
        remove() { if (this.parentNode) { this.parentNode.removeChild(this); } },
        setAttribute(k, v) { this.attributes[k] = v; },
        getAttribute(k) { return (k in this.attributes) ? this.attributes[k] : null; },
        addEventListener() {},
        removeEventListener() {},
        dispatchEvent() { return true; },
        getBoundingClientRect() {
            return { left: 0, top: 0, width: 800, height: 600, right: 800, bottom: 600 };
        },
        focus() {},
        blur() {},
        createSVGRect() { return {}; }, // Browser.svg 检测位：缺了 L.svg() 返回 null
    };
}

const doc = {
    createElement: makeEl,
    createElementNS: (ns, tag) => makeEl(tag),
    createTextNode: (t) => ({ nodeType: 3, textContent: String(t), parentNode: null }),
    documentElement: makeEl('html'),
    body: makeEl('body'),
    addEventListener() {},
    removeEventListener() {},
    getElementsByTagName: () => [],
    querySelector: () => null,
    querySelectorAll: () => [],
    hidden: false,
};
doc.documentElement.appendChild(doc.body);

// Leaflet 多处 instanceof 检查这些构造器（DivIcon 查 options.html instanceof Element）
global.Element = class Element {};
global.HTMLElement = class HTMLElement extends global.Element {};
global.SVGElement = class SVGElement extends global.Element {};
global.Node = class Node {};

global.document = doc;
global.window = global;
global.self = global;
// Node 24 的 global.navigator 是 getter-only，需 defineProperty 覆盖
Object.defineProperty(global, 'navigator', {
    value: { userAgent: 'node-headless', platform: 'node' },
    configurable: true,
    writable: true,
});
global.screen = { width: 800, height: 600, availWidth: 800, availHeight: 600 };
global.devicePixelRatio = 1;
global.Image = function () { return makeEl('img'); };
global.addEventListener = () => {};
global.removeEventListener = () => {};
global.requestAnimationFrame = (fn) => setTimeout(fn, 0);
global.cancelAnimationFrame = clearTimeout;
