# libdmx 1.1.5 adaptation notes

## Upstream identity

- Source: https://xorg.freedesktop.org/archive/individual/lib/libdmx-1.1.5.tar.xz
- sha256: 35a4e26a8b0b2b4fe36441dca463645c3fa52d282ac3520501a38ea942cbf74f
  (verified locally against the tarball; matches the freedesktop release)
- License: MIT (COPYING; Copyright 2002-2004 Red Hat Inc., Durham,
  North Carolina)
- Homepage: https://gitlab.freedesktop.org/xorg/lib/libdmx

## Build system

- Autotools (configure + make).  `PKG_CHECK_MODULES(DMX,
  [x11 >= 1.6] xext xextproto [dmxproto >= 2.2.99.1])`.
- Single translation unit `src/dmx.c` producing `libdmx.la` with
  `-version-number 1:0:0 -no-undefined` → `libdmx.so.1.0.0`,
  soname `libdmx.so.1`.
- Installs: `include/X11/extensions/dmxext.h`, `lib/libdmx.so*`,
  `lib/pkgconfig/dmx.pc`, man3 pages.

## Upstream test inventory (R51 三步法 step 1)

- `Makefile.am` / `src/Makefile.am` / `man/Makefile.am` declare no
  TESTS, check_PROGRAMS, check-local, or custom test target.
- `make check` runs and reports zero tests (verified in the OHOS build
  below: PASS with "No test target" semantics).
- Upstream zero-test evidence: no test/ directory in the release
  tarball; the only non-build outputs are man pages.

## Dependencies (all on the cmd-pkgs track, no vendoring)

- `libx11/6.4.0` — Xlib runtime (`-lX11`), provides Xlib.h/Xlibint.h.
- `libxext/6.4.0.1` — Xext + extutil runtime (`-lXext`), provides
  Xext.h/extutil.h. libdmx uses XEXT_GENERATE_FIND_DISPLAY from
  extutil.h for its extension bookkeeping.
- `xorgproto/2025.1` — headers-only; provides dmx.h + dmxproto.h and
  dmxproto.pc (Version 2.3.1, satisfies upstream `dmxproto >= 2.2.99.1`),
  plus xextproto.pc for the configure check.
- libxcb/libxau/libxdmcp/xtrans remain transitive deps of libX11.

## OHOS adaptation decisions

- Dependency track selection: the recipe requires libxext. The remote
  (ohpcd) publishes libxext only as 6.4.0/6.4.0.1 (cmd-pkgs ABI track,
  upstream libXext 1.3.6). libxext/1.3.7 exists in-repo but has no
  published binaries, so the build would require building libXext 1.3.7
  from source first — out of scope for a single-package PR (one software
  per PR). Chosen track: libx11/6.4.0 + libxext/6.4.0.1 +
  xorgproto/2025.1, matching the CI-verified libxres/1.2.1 pattern.
- No source patches. The OHOS quirks are handled in the recipe:
  - `_patch_configure_runtime_shell()`: umask 077 → 022 and the
    /bin/sh shebang → an executable shell, mirroring libxext/6.4.0.1.
  - `--build/--host aarch64-unknown-linux-gnu` passed explicitly
    because the bundled config.guess does not know ohos
    (same rationale as libxext/6.4.0.1; canonicalization only).
  - `DMX_CFLAGS`/`DMX_LIBS` injected from dependency package folders so
    configure's PKG_CHECK_MODULES variables resolve without a system
    pkg-config database.
  - `_fix_dep_la_files()` (E331/E237): dependency .la cleanup.
- `.la` files are not shipped; `dmx.pc` is rewritten to be
  pcfiledir-relative.

## Test design (why no X server is needed)

Every public DMX function dereferences a `Display *` (via
`find_display(dpy)` / `XextCheckExtension`), so no public function can
be safely called with a NULL display. The test_package therefore
validates the installed package without a server:

1. `api_surface.c` — live typed relocation against all 18 exported
   symbols; a missing implementation fails at link or load.
2. `version_contract.c` — protocol version constants, all request
   opcodes, wire sizes, dmx.h/dmxproto.h error-code agreement, mask
   values, and ABI struct field round-trips.
3. `ohos_abi_contract.c` (HarmonyOS-specific) — the consumer executes
   on the OHOS target, proving the dynamic linker resolves libdmx.so.1
   and its transitive closure; the recipe's test() additionally runs an
   ELF gate (ELF64, AArch64, NEEDED contains libXext.so.6 + libX11.so.6,
   no absolute Conan RPATH/RUNPATH) via readelf before executing.

## Build log (ohos-aarch64, device-native clang)

See `.ci-result.json` for the machine-readable record.

- `conan create archives/l/libdmx/1.1.5 --build=missing
  -pr:h ci/conan/profiles/ohos-aarch64 -pr:b
  ci/conan/profiles/ohos-aarch64` — shared + static package builds.
- `make check` executed in both package builds (zero upstream tests,
  exit 0).
- test_package executed for both shared and static with the ELF gate.

## Verification results

- py_compile: PASS (recipe + test_package).
- git diff --check: clean.
- No local paths, no caches, no stray files in the archive tree.
