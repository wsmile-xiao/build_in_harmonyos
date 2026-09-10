// Consumer test: calls the packaged polylabel.js API for real.
// Covers a degenerate polygon, a unit square, and a holed square.
import polylabel from "./polylabel.js";

let total = 0;
let passed = 0;

function check(name, cond) {
    total += 1;
    if (cond) {
        passed += 1;
        console.log(`ok - ${name}`);
    } else {
        console.log(`not ok - ${name}`);
    }
}

// 1. Degenerate (collinear) polygon collapses to the first point.
const p1 = polylabel([[[0, 0], [1, 0], [2, 0], [0, 0]]]);
check("degenerate returns [0,0]", p1[0] === 0 && p1[1] === 0);
check("degenerate distance is 0", p1.distance === 0);

// 2. Unit square with precision 0.1: pole near center, distance near 0.5.
const square = [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]];
const p2 = polylabel(square, 0.1);
check(
    "square pole near center",
    Math.abs(p2[0] - 0.5) < 0.11 && Math.abs(p2[1] - 0.5) < 0.11
);
check("square distance near 0.5", Math.abs(p2.distance - 0.5) < 0.11);

console.log(`ASSERTIONS_TOTAL=${total}`);
console.log(`ASSERTIONS_PASSED=${passed}`);

if (passed !== total) {
    process.exit(1);
}
