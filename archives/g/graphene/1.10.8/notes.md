# graphene 1.10.8 HarmonyOS PC adaptation notes

Issue: 无独立 Issue（HarmonyOS PC 三方库适配，积分赛提交）
Branch: feat/graphene-1.10.8
Target path: archives/g/graphene/1.10.8

## Summary

Graphene 1.10.8 is a thin layer of graphic data types for 2D/3D math
(points, vectors, matrices, quaternions, euler angles, planes, frusta,
spheres, boxes, rays, rectangles, triangles and sizes). It is a pure C,
MIT-licensed library built with Meson. Its only upstream dependency is
GLib (glib-2.0 >= 2.30, used for the optional GObject types).

The OHOS Conan profile maps `os=OHOS` to Meson `host_system='harmonyos'`.
Graphene's build has no Linux-specific code paths that break on HarmonyOS,
so this first round ships **no patches** and a static build.

## Build Configuration

The recipe builds a static package:

```text
default_library=static
wrap_mode=nodownload
introspection=disabled
installed_tests=false
gtk_doc=false
tests=true
```

`tests=true` is intentional. On native OHOS/HarmonyOS builds, the recipe runs
upstream Meson tests in `build()`:

```sh
meson test -v -C "<build-folder>" --timeout-multiplier=16 --no-rebuild --no-suite=failing
```

## Dependency Strategy

- `glib2/2.88.0` is the only dependency, consumed with
  `transitive_headers=True, transitive_libs=True`.
- The `glib2` conan package exposes `pkg_config_name=glib-2.0`, so
  `PkgConfigDeps` generates `glib-2.0.pc` (Version 2.88.0). Graphene's Meson
  looks up `gobject-2.0`; the recipe adds a small forwarding
  `gobject-2.0.pc` (`Requires: glib-2.0`, version inherited = 2.88.0) so the
  pkg-config chain resolves glib 2.88.0 end-to-end.
- Graphene's test suite needs `mutest`; the upstream tarball already vendors
  `subprojects/mutest`, which builds offline under `wrap_mode=nodownload`.

## Patch Summary

| Patch | Purpose |
|------|---------|
| (none) | Round 1 static build, no patches required. |

## True-device Validation

Validation was run on HarmonyOS PC device with the OHOS aarch64 Conan profile.

Command:

```sh
cd /storage/Users/currentUser/build_in_harmonyos
CI_PACKAGES="archives/g/graphene/1.10.8" /usr/bin/zsh ci/conan/build_and_test.sh
```

Logs:

```text
/storage/Users/currentUser/.local/state/oh-device-porting/runs/graphene-1.10.8/logs/build-round-01.log
```

Configure-stage pkg-config evidence (glib 2.88.0 resolved through generated
.pc, no manual PKG_CONFIG_PATH export):

```text
graphene/1.10.8: pkg-config evidence: glib-2.0.pc Version: 2.88.0
Run-time dependency gobject-2.0 found: YES 2.88.0
```

Upstream Meson test result from this true-device run:

| Result | Count | Notes |
|------|------:|------|
| Ok | 21 | 18 graphene unit tests + 3 mutest subproject tests. |
| Fail | 0 | No failed upstream tests. |
| Skipped | 0 | No platform/tooling skips. |

Actual executed-test pass rate: `21/21 = 100%`.

Test detail (18 graphene suites, subtests all passed):
box 65, euler 10, frustum 21, matrix 70, plane 13, point 24, point3d 36,
quad 12, quaternion 24, ray 26, rect 69, simd 35, size 17, sphere 17,
triangle 56, vec2 37, vec3 51, vec4 63 subtests.

Single-package CI result:

```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: no bin/ dir (library package)
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content
```

`test_package` also passed and executed a graphene consumer smoke test:

```text
graphene/1.10.8 (test package): RUN: /data/service/hnp/bin/bash -c './test_graphene'
graphene point3d OK
```

L1e destructive negative test confirmed the test genuinely depends on the
package (lib/ moved away → re-run fails → restored).

## Skipped Test Explanation

No upstream tests skipped (0 Skipped). `L2_RESULT=skip` refers to the CI
smoke-test stage (no `bin/` in a library package), not to upstream tests.

The `meson test` invocation passes `--no-suite=failing`. This flag only
excludes tests tagged with the `failing` suite; upstream graphene 1.10.8
defines **no** `failing` suite (verified: `tests/meson.build` contains no
`suite`/`failing` markers), so it is a no-op and the 21/21 result covers the
full upstream test set.

## Notes

- mutest subproject tests (general/hooks/types) run as part of `meson test`
  and are counted in the 21 Ok.
- SIMD paths: ARM NEON enabled (graphene_has_neon=1), SSE/GCC-vector
  disabled on aarch64 (expected).
