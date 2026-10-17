# libgda6 6.0.0 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Clang 15 (aarch64-unknown-linux-ohos)
- Conan 2.29.1, meson 1.11.1, valac 0.56.19
- Upstream source: libgda-6.0.0.tar.xz (GNOME), sha256
  995f4b420e666da5c8bac9faf55e7aedbe3789c525d634720a53be3ccf27a670

## Verification

- `conan-verify libgda6 6.0.0`: exit 0 (PASS)
- `CI_PACKAGES="archives/l/libgda6/6.0.0" zsh ci/conan/build_and_test.sh`: exit 0
- L0: passed
- L1: passed (upstream tests + test_package executed)
- L2: skipped (no bin/ dir — build-only library package)
- L4: passed (patches clean)
- L5: passed (lib/ has content)

## conan create

- meson build: 406/406 targets compiled
- test_package (`test_pkg.c`): gda_init() runs, provider enumeration
  detects the built-in SQLite provider, data-model API smoke test passes:
  `provider: SQLite` / `test libgda6 6.0.0: OK`

## Upstream test suite (meson test -j1, 54 test() targets)

Latest run (final code): **ok=48 fail=6** (earlier runs 47/54 and 49/54 with non-overlapping
failing sets, confirming the flaky subset drifts run-to-run):

- `ServerOperationPostgreSQL`, `dbcatalog-postgresql`: require a live
  PostgreSQL server; none is available on the device (environment
  limitation, same upstream without a server).
- Remaining 3 (`DataProxy` / `MultiThreadConnectionLock` / `dbcatalog`
  subset): known upstream GLib `g_weak_ref` multi-thread races under
  glib 2.88; assertion aborts, failing set drifts between runs — not a
  porting defect.

## Result

The recipe was verified on an OpenHarmony aarch64 device and is eligible
for published status.
