# HarfBuzz 14.4.0 adaptation notes

## Source and scope

- Official source: `harfbuzz-14.4.0.tar.xz` (Meson dist tarball from the
  upstream GitHub release)
- SHA-256: `2357ed966c6ced7bfa720b0640c0231065af01158fbea215093ffa15aed44371`
- Build system: Meson
- Delivery default: `shared=True`, required by Pango consumers

## Relationship to 14.3.0

This is a version bump on the 14.3.0 recipe. The recipe logic is unchanged;
only the pinned source URL/SHA-256 and the reported version moved.

- `meson_options.txt` is **byte-identical** between 14.3.0 and 14.4.0
  (3790 bytes each, compared via the upstream tag files), so every option the
  recipe sets/unsets still exists and the configure surface is unchanged.
- Upstream `meson.build` is identical as well for the option plumbing.

## Dependency decision

The 14.4.0 source exposes GLib, GObject, Cairo, zlib, ICU, Graphite2, Rust,
platform shapers, and demo integrations as optional Meson features. This
candidate keeps the 14.3.0 dependency decision: disable those providers and
keep only `freetype/2.14.3` as a Conan dependency. The current FreeType recipe
has no Conan requirements and passes `--with-harfbuzz=no`, so the graph stays
acyclic.

## Test design

Unchanged from 14.3.0: `tests=enabled` and `utilities=enabled` expose the
upstream API, fuzzing, threads, subset, shape, and vector Meson suites;
`MESON_TESTTHREADS=1` keeps execution bounded. On Linux/OHOS, `NM`, `OBJDUMP`,
and an `LDD`-compatible `llvm-readelf -d` command are resolved from the
configured Clang toolchain so the upstream distribution checks execute instead
of self-skipping for a missing helper.

`HARFBUZZ_SOURCE_ARCHIVE` may point to the frozen official tarball for a local
run; the recipe converts only that verified regular file to `file://` and still
enforces the unchanged `conandata.yml` SHA-256 through `get()`.
`HARFBUZZ_UPSTREAM_EVIDENCE_DIR`, when set, copies the raw Meson introspection
inventory and JSONL/text test logs into that task-local directory.

The upstream suite grew between the two releases (new API tests such as
`test-subset-avar2.c`, new fuzzing targets, and additional shape/subset data),
so the executed count is re-measured from the CI `meson test` summary rather
than carried over from 14.3.0.

## Verification

- Upstream tests run in `build()` via `meson test -v`; the exact
  `Ok: N / Fail: 0` summary is recorded in `test_package/MANIFEST.yml`.
- Consumer test: `test_package/test.c` links `harfbuzz::harfbuzz`, asserts the
  14.4.0 version floor, exercises the shaping pipeline on an inline string, and
  calls `hb_ot_fetch_number` on the empty face.
