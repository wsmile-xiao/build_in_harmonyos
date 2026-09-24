# libdvbv5 1.32.0 OpenHarmony adaptation record

## Basic information

- Software: libdvbv5
- Upstream project: v4l-utils (lib/libdvbv5 subtree)
- Version: 1.32.0
- Build system: Meson
- Target: OHOS aarch64 (HarmonyOS PC)
- Source: `https://linuxtv.org/downloads/v4l-utils/v4l-utils-1.32.0.tar.xz`
  (sha256 `6828828a17775526eb93fb258a9294d1d1073d633c344dd71ecd4e7a1ffb7dfc`)

## Scope

Upstream never publishes libdvbv5 on its own; it lives in the v4l-utils source
tree as `lib/libdvbv5`. This package therefore builds the official v4l-utils
release tarball with `-Dlibdvbv5=enabled` and everything else disabled, and
packages the resulting `libdvbv5.so.0` plus its 47 public headers.

A sibling archive already exists for the libv4l half of the same tarball
(`archives/v/v4l/1.32.0`, which sets `-Dlibdvbv5=disabled`). Upstream's
`lib/meson.build` has no option to build `libdvbv5` alone — it always descends
into `libv4lconvert`, `libv4l2`, `libv4l1` and `libv4l2rds` as well. Those four
libraries and their headers/`.pc` files belong to the `v4l` package, so
`package()` prunes them. The shipped surface is `libdvbv5.so.0` with its
SONAME/linker aliases, 47 public headers, `libdvbv5.pc`, both licence files
and the `libdvbv5.mo` / `v4l-utils.mo` gettext catalogues (9 files across 5
locales). The pruning is prefix-based on `libv4l`, so the five `v4l-utils.mo`
catalogues are intentionally left in place.

## Dependencies

`libudev` is a hard requirement — `lib/libdvbv5/meson.build` calls
`subdir_done()` when `dep_libudev` is not found. It is provided by
`eudev/3.2.14` from the ohpcd remote; `PkgConfigDeps` generates its
`libudev.pc` so upstream's `dependency('libudev')` probe succeeds.

## Platform findings

| # | Finding | Impact | Handling |
|---|---|---|---|
| 1 | OHOS/musl has no `argp` library and no `argp_parse` symbol. | Upstream's `cc.find_library('argp')` is a hard probe; the whole configure aborts with `C shared or static library 'argp' not found` even though only optional utilities use it. | Patch `meson.build` to `required : false`. |
| 2 | OHOS/musl ships no usable libintl. The sysroot's `libintl.h` declares no functions and libc exports no `gettext` symbols. | Upstream's `dependency('intl')` is required, and `-DENABLE_NLS` unconditionally selects the real-libintl branch of `include/gettext.h`, producing undeclared `dgettext`/`dcgettext` and link failures. | Make the dependency optional and only define `ENABLE_NLS` when `dep_intl.found()`; `gettext.h`'s NLS-disabled branch then expands the message macros to no-ops. |
| 3 | The top-level `include/` directory is only added to the include path when `host_machine.system() == 'linux'`. | Meson reports OHOS as `harmonyos`, so `gettext.h` is not found and 10 libdvbv5 sources fail to compile. | Add `harmonyos` to that branch. |
| 4 | The OHOS UAPI headers do not define `V4L2_PIX_FMT_NV12_16L16`. | `lib/libv4lconvert/libv4lconvert.c` fails to compile (the format table and a switch case reference it). | Provide the canonical fourcc under `#ifndef V4L2_PIX_FMT_NV12_16L16`. |
| 5 | musl does not provide `pthread_cancel`. | `libdvbv5.so` fails to link with `undefined symbol: pthread_cancel`; the symbol is used in the udev monitor thread and the remote receiver thread. | Replace cancellation with cooperative shutdown: a stop flag polled by the monitor's 1-second `select()` timeout, and a socket `shutdown()` that unblocks `recv()`, each followed by `pthread_join`. |
| 6 | OHOS refuses to load unsigned shared objects. | A consumer linking the library aborts with `Error loading shared library libdvbv5.so.0`. | `package()` signs every ELF under `lib/` and `bin/` with `binary-sign-tool -selfSign 1`. |
| 7 | Meson does not create the SONAME symlinks on OHOS. | Consumers link via `libdvbv5.so` while the loader needs `libdvbv5.so.0`. | `package()` materialises `.so` and intermediate SONAME aliases as real copies. |

## Build flow

```bash
conan create archives/l/libdvbv5/1.32.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  -r=ohpcd --build=missing
```

Meson options used: `-Dlibdvbv5=enabled` plus `-Dbpf/-Dgconv/-Djpeg/
-Dqv4l2/-Dqvidcap/-Dv4l2-tracer/-Ddoxygen-doc=disabled` and
`-Dv4l-utils/-Dv4l-plugins/-Dv4l-wrappers=false`.

## Verification

Real build executed on an OHOS aarch64 worker:

- `conan create` exit code **0**.
- `test_package` (L1 consumer test): **19/19 assertions passed**, exit code 0.
- Packaged artefact: `libdvbv5.so.0.0.0` (ELF64 AArch64, SONAME
  `libdvbv5.so.0`, NEEDED `libudev.so.1`, `libc.so`), 47 headers,
  `libdvbv5.pc`.

## Upstream tests

`meson test -C build --list` reports **`No tests defined.`** — upstream
registers zero tests. The only non-device consumer of libdvbv5 is
`utils/dvb/dvb-format-convert`, which needs `argp` and therefore cannot be
built on OHOS. Its libdvbv5 code path (`dvb_read_file_format` →
`dvb_write_file_format`) was exercised equivalently and passed a 3-channel
round-trip. Full inventory and per-entry technical reasons:
`1.32.0/reports/upstream-tests.md`.

## OHOS-specific test

`test_package/test_libdvbv5.c` adds `test_ohos_packaging`, which asserts that a
consumer binary built against the packaged library links and runs on OHOS —
i.e. that the package was correctly signed and exposes the SONAME the loader
requires. Upstream has no test covering the packaged artefact.

## Known limits

`libdvbv5` talks to DVB frontends, demuxers and udev at runtime. This worker
has no `/dev/dvb/adapter*/frontend0`, so live tuning, scanning and zapping
cannot be validated here; the test surface covers the file-format API, the
parser error paths and the packaged-artefact contract.
