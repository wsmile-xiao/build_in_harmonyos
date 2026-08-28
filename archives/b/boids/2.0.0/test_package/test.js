/* boids 2.0.0 — functional test suite (complementary; upstream ships no tests)
 * Runs with: NODE_PATH=<module root> node test.js
 * Exits non-zero on any failure. Every case asserts the public API contract.
 */
'use strict';
var assert = require('assert');
var Boids = require('boids');

var passed = 0;
function ok(name, fn) {
  try { fn(); passed += 1; console.log('  PASS ' + name); }
  catch (e) { console.error('  FAIL ' + name + ': ' + e.message); process.exitCode = 1; }
}

// 1. module-load: require returns a constructor
ok('module exports a constructor', function () {
  assert.strictEqual(typeof Boids, 'function');
});

// 2. factory call without `new`
ok('factory call (no new) works', function () {
  var f = Boids({ boids: 5 });
  assert.ok(f instanceof Boids);
  assert.strictEqual(f.boids.length, 5);
});

// 3. default boid count is 50
ok('default boid count is 50', function () {
  assert.strictEqual(new Boids().boids.length, 50);
});

// 4. custom boid count honored
ok('custom boid count honored', function () {
  assert.strictEqual(new Boids({ boids: 10 }).boids.length, 10);
});

// 5. boid record shape: [x, y, vx, vy, ax, ay], all finite numbers
ok('boid records are 6-element finite arrays', function () {
  var f = new Boids({ boids: 50 });
  f.boids.forEach(function (b) {
    assert.ok(Array.isArray(b));
    assert.strictEqual(b.length, 6);
    assert.ok(b.every(function (n) { return typeof n === 'number' && isFinite(n); }));
  });
});

// 6. initial speeds/accelerations are zero
ok('initial speeds/accelerations are zero', function () {
  var f = new Boids({ boids: 3 });
  f.boids.forEach(function (b) {
    assert.strictEqual(b[2], 0);
    assert.strictEqual(b[3], 0);
    assert.strictEqual(b[4], 0);
    assert.strictEqual(b[5], 0);
  });
});

// 7. single boid with zero speed stays in place
ok('single boid with zero speed stays in place', function () {
  var f = new Boids({ boids: 1 });
  var p = f.boids[0].slice(0, 2);
  f.tick();
  assert.deepStrictEqual(f.boids[0].slice(0, 2), p);
});

// 8. position integration: boid moves by its speed each tick
ok('position integrates speed each tick', function () {
  var f = new Boids({ boids: 1 });
  f.boids[0][0] = 10; f.boids[0][1] = 20;
  f.boids[0][2] = 1.5; f.boids[0][3] = -0.5;
  f.tick();
  assert.strictEqual(f.boids[0][0], 11.5);
  assert.strictEqual(f.boids[0][1], 19.5);
});

// 9. speedLimit constrains boid speed
ok('speedLimit constrains speed', function () {
  var f = new Boids({ boids: 1, speedLimit: 2 });
  f.boids[0][2] = 10; f.boids[0][3] = 0;
  f.tick();
  var s2 = f.boids[0][2] * f.boids[0][2] + f.boids[0][3] * f.boids[0][3];
  assert.ok(s2 <= 2 * 2 + 1e-9, 'speed^2=' + s2);
});

// 10. accelerationLimit constrains accumulated acceleration
ok('accelerationLimit constrains acceleration', function () {
  var f = new Boids({ boids: 1, accelerationLimit: 1 });
  f.attractors.push([0, 0, 100, 100]);          // huge attractor to demand > limit
  f.boids[0][0] = 50; f.boids[0][1] = 0;        // inside attractor radius
  f.tick();
  var a2 = f.boids[0][4] * f.boids[0][4] + f.boids[0][5] * f.boids[0][5];
  assert.ok(a2 <= 1 * 1 + 1e-9, 'accel^2=' + a2);
});

// 11. attractor pulls boid velocity toward it
ok('attractor pulls boid toward it', function () {
  var f = new Boids({ boids: 1 });
  f.attractors.push([5, 0, 10, 2]);             // (x, y, radius, force)
  f.boids[0][0] = 0; f.boids[0][1] = 0;
  f.tick();
  assert.ok(f.boids[0][2] > 0, 'vx=' + f.boids[0][2]);   // x-speed grows toward attractor
  assert.ok(f.boids[0][0] > 0, 'x=' + f.boids[0][0]);    // position moves toward attractor
});

// 12. two close boids repel each other (separation)
ok('separation pushes close boids apart', function () {
  var f = new Boids({ boids: 2, separationDistance: 10, separationForce: 0.5 });
  f.boids[0][0] = 0; f.boids[0][1] = 0;
  f.boids[1][0] = 3; f.boids[1][1] = 0;
  var d0 = Math.abs(f.boids[0][0] - f.boids[1][0]);
  f.tick(); f.tick();
  var d1 = Math.abs(f.boids[0][0] - f.boids[1][0]);
  assert.ok(d1 > d0 + 1e-9, 'distance ' + d0 + ' -> ' + d1);
});

// 13. cohesion accelerates a boid toward its neighbours' centroid
ok('cohesion accelerates toward neighbours', function () {
  var f = new Boids({ boids: 2, separationDistance: 5, cohesionDistance: 200,
                      cohesionForce: 0.5, alignmentForce: 0,
                      accelerationLimit: 0, speedLimit: 0 });
  f.boids[0][0] = 0; f.boids[0][1] = 0;   // A
  f.boids[1][0] = 10; f.boids[1][1] = 0;  // B
  f.tick();
  assert.ok(f.boids[0][4] > 0.3, 'A accel x=' + f.boids[0][4]);   // A accelerates toward B (+x)
  assert.ok(f.boids[1][4] < -0.3, 'B accel x=' + f.boids[1][4]);  // B accelerates toward A (-x)
});

// 14. alignment impulse follows neighbour velocity (implemented semantics)
ok('alignment impulse reflects neighbour velocity', function () {
  var g = new Boids({ boids: 2, alignmentDistance: 200, alignmentForce: 0.5,
                      separationDistance: 1, cohesionDistance: 1,
                      accelerationLimit: 0, speedLimit: 0 });
  g.boids[0][0] = 0;  g.boids[0][1] = 0;
  g.boids[1][0] = 10; g.boids[1][1] = 0;
  g.boids[1][2] = 5;  g.boids[1][3] = 0;      // neighbour moves +x
  g.tick();
  assert.ok(Math.abs(g.boids[0][4] + 0.5) < 1e-9, 'A accel x=' + g.boids[0][4]);
});

// 15. boid count remains stable across many ticks
ok('boid count stable over 100 ticks', function () {
  var f = new Boids({ boids: 20 });
  for (var i = 0; i < 100; i++) f.tick();
  assert.strictEqual(f.boids.length, 20);
});

// 16. 'tick' event fires with the boids payload
ok('tick event emits boids payload', function () {
  var f = new Boids({ boids: 4 });
  var got = null;
  f.on('tick', function (b) { got = b; });
  f.tick();
  assert.strictEqual(got, f.boids);
});

// 17. long-run robustness: no NaN over 1000 ticks
ok('no NaN over 1000 ticks', function () {
  var f = new Boids({ boids: 40, speedLimit: 3, accelerationLimit: 1,
                      attractors: [[10, 10, 30, 1], [200, 200, 30, -1]] });
  for (var i = 0; i < 1000; i++) f.tick();
  f.boids.forEach(function (b) {
    assert.ok(b.every(function (n) { return typeof n === 'number' && isFinite(n); }));
  });
});

console.log('\n' + passed + ' tests passed');
if (process.exitCode) { console.error('SOME TESTS FAILED'); process.exit(1); }