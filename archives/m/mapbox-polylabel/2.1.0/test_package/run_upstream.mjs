// Upstream rerun (cache-proof): same 4 cases as upstream test/test.js,
// run against the PACKAGED polylabel.js + vendored tinyqueue.
// Fixtures are byte-identical copies of upstream test/fixtures/*.json.
// Engine: node (18+, JSON import attributes). qjs fallback is handled
// inside test_package/conanfile.py using the same fixtures + oracles.
import polylabel from "./polylabel.js";
import assert from "node:assert/strict";
import water1 from "./fixtures/water1.json" with { type: "json" };
import water2 from "./fixtures/water2.json" with { type: "json" };
import fs from "node:fs";

// Anti-false-pass: fixtures must be non-empty (toybox empty-file pit).
const w1raw = fs.readFileSync(new URL("./fixtures/water1.json", import.meta.url), "utf-8");
const w2raw = fs.readFileSync(new URL("./fixtures/water2.json", import.meta.url), "utf-8");
if (w1raw.length < 1000 || w2raw.length < 1000) {
    console.log(`not ok - fixtures empty (water1 ${w1raw.length}B, water2 ${w2raw.length}B)`);
    console.log("# tests 4");
    console.log("# pass 0");
    console.log("# fail 4");
    process.exit(1);
}
if (!Array.isArray(water1) || water1.length === 0 || water1[0].length < 100) {
    console.log("not ok - water1 polygon has no points");
    console.log("# tests 4");
    console.log("# pass 0");
    console.log("# fail 4");
    process.exit(1);
}
if (!Array.isArray(water2) || water2.length === 0 || water2[0].length < 100) {
    console.log("not ok - water2 polygon has no points");
    console.log("# tests 4");
    console.log("# pass 0");
    console.log("# fail 4");
    process.exit(1);
}
console.log(`fixtures ok (water1 ${w1raw.length}B/${water1[0].length}pts, water2 ${w2raw.length}B/${water2[0].length}pts)`);

let passed = 0;
let failed = 0;
function run(name, fn) {
    try {
        fn();
        passed += 1;
        console.log(`ok - ${name}`);
    } catch (e) {
        failed += 1;
        console.log(`not ok - ${name}: ${e && e.message ? e.message.split("\n")[0] : e}`);
    }
}

run("finds pole of inaccessibility for water1 and precision 1", () => {
    const p = polylabel(water1, 1);
    assert.deepEqual(p, Object.assign([3865.85009765625, 2124.87841796875], { distance: 288.8493574779127 }));
});

run("finds pole of inaccessibility for water1 and precision 50", () => {
    const p = polylabel(water1, 50);
    assert.deepEqual(p, Object.assign([3854.296875, 2123.828125], { distance: 278.5795872381558 }));
});

run("finds pole of inaccessibility for water2 and default precision 1", () => {
    const p = polylabel(water2);
    assert.deepEqual(p, Object.assign([3263.5, 3263.5], { distance: 960.5 }));
});

run("works on degenerate polygons", () => {
    let p = polylabel([[[0, 0], [1, 0], [2, 0], [0, 0]]]);
    assert.deepEqual(p, Object.assign([0, 0], { distance: 0 }));
    p = polylabel([[[0, 0], [1, 0], [1, 1], [1, 0], [0, 0]]]);
    assert.deepEqual(p, Object.assign([0, 0], { distance: 0 }));
});

console.log(`# tests 4`);
console.log(`# pass ${passed}`);
console.log(`# fail ${failed}`);
if (failed > 0 || passed !== 4) {
    process.exit(1);
}
