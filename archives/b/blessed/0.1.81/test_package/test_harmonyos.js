// 鸿蒙专属测试：6 项功能性断言
// 关键：用 PassThrough 作为 screen 的 input/output，避免绑定真实 tty 导致 node 挂起
const { PassThrough } = require('stream');
const blessed = require('blessed');
const assert = require('assert');

// 断言 1: 核心 API 导出
assert.strictEqual(typeof blessed.screen, 'function');
assert.strictEqual(typeof blessed.box, 'function');
assert.strictEqual(typeof blessed.list, 'function');
assert.strictEqual(typeof blessed.button, 'function');
assert.strictEqual(typeof blessed.text, 'function');
console.log('PASS: Core API exports');

// 使用无 tty 绑定的 screen
const input = new PassThrough();
const output = new PassThrough();
const screen = blessed.screen({
    input: input,
    output: output,
    terminal: 'dumb',
    smartCSR: true,
    warnings: false
});

// 断言 2: Screen 实例创建
assert.ok(screen);
console.log('PASS: Screen instance');

// 断言 3: Box 实例创建
const box = blessed.box({ parent: screen, content: 'Hello OHOS', border: { type: 'line' } });
assert.ok(box);
console.log('PASS: Box instance');

// 断言 4: 内容属性操作
box.setContent('Updated');
assert.strictEqual(box.getContent(), 'Updated');
console.log('PASS: Content manipulation');

// 断言 5: 事件系统
let fired = false;
box.on('test-event', () => { fired = true; });
box.emit('test-event');
assert.strictEqual(fired, true);
console.log('PASS: Event system');

// 断言 6: List 组件
const list = blessed.list({ parent: screen, items: ['A', 'B', 'C'] });
assert.strictEqual(list.items.length, 3);
console.log('PASS: List component');

screen.destroy();
console.log('ALL_HARMONYOS_TESTS_PASSED');
process.exit(0);
