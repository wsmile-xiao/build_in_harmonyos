// 上游冒烟测试：验证 blessed 核心 API 导出与实例创建
// 关键：用 PassThrough 作为 screen 的 input/output，避免绑定真实 tty 导致 node 挂起
const { PassThrough } = require('stream');
const blessed = require('blessed');

if (typeof blessed.screen !== 'function') { console.error('FAIL: screen'); process.exit(1); }
if (typeof blessed.box !== 'function') { console.error('FAIL: box'); process.exit(1); }
if (typeof blessed.list !== 'function') { console.error('FAIL: list'); process.exit(1); }
if (typeof blessed.button !== 'function') { console.error('FAIL: button'); process.exit(1); }

try {
    const input = new PassThrough();
    const output = new PassThrough();
    const screen = blessed.screen({
        input: input,
        output: output,
        terminal: 'dumb',
        smartCSR: true,
        warnings: false
    });
    if (!screen) { console.error('FAIL: screen instance'); process.exit(1); }

    const box = blessed.box({ parent: screen, content: 'test' });
    if (!box) { console.error('FAIL: box instance'); process.exit(1); }
    if (box.getContent() !== 'test') { console.error('FAIL: box content'); process.exit(1); }

    screen.destroy();
} catch (e) {
    console.error('FAIL:', e.message);
    process.exit(1);
}

console.log('UPSTREAM_SMOKE_TEST_PASSED');
process.exit(0);
