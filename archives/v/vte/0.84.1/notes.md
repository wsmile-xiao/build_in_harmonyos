# vte 0.84.1 notes

## Scope

Version-follow of the archived `vte/0.74.2` onto the 0.84 line
(task #14257). Library API family stays `vte-2.91` but the flavour is
**gtk4** (0.74.2 was gtk3): soname `libvte-2.91-gtk4.so`, pkg-config
name `vte-2.91-gtk4`, headers under `include/vte-2.91-gtk4`.

## Upstream

- Tag: 0.84.1 (gitlab.gnome.org/GNOME/vte — no v prefix)
- Tarball: https://download.gnome.org/sources/vte/0.84/vte-0.84.1.tar.xz
- SHA256: `aca1caa8478aebcdbb1d67897fb3511eb7601debae6810e16a15b6fa25f31ac8`

## Dependency delta vs 0.74.2 (meson.build @ 663-705)

| dep | 0.74.2 | 0.84.1 | resolution |
|---|---|---|---|
| liblz4 | — | NEW (>= 1.9.4) | conan `lz4/1.10.0.1` |
| simdutf | — | NEW (>= 6.2.0) | **vendored subproject** 8.2.0 (tarball ships full source + own meson.build; registry 6.0.3 too old) |
| fmt | — | NEW (optional system, header-only) | conan `fmt/9.1.0` (fmt_sysdep found → -DFMT_HEADER_ONLY path, no subproject) |
| pcre2 | ✓ | ✓ | same alias .pc forward (libpcre2-8) |
| gtk | gtk3 | gtk4=true, gtk3=false | gtk4/4.22.4 Broadway-only stack |

## OHOS adaptations (0.74.2 recipe carry-overs, proven on CI)

- `b_ndebug=false` (upstream asserts it)
- `W_EXITCODE` macro define (musl has no sys/wait.h version)
- libpcre2-8.pc alias generation
- glib tool variable injection into gio-2.0.pc/glib-2.0.pc
- meson native [binaries] ar/ranlib + glib tool pinning
- buildenv LD_LIBRARY_PATH: all dep libdirs + `/system/lib64`
- `.so` re-sign with binary-sign-tool (OHOS loader .codesign)
- Disabled: gir/vapi/docs/glade/gnutls/icu/_systemd/fribidi/a11y/app

## simdutf vendored subproject (key learning)

`dependency('simdutf', version: '>= 6.2.0', required: true, default_options: …)`
falls back to `subproject('simdutf')` when the system dep is absent.
The release tarball **pre-populates** `subprojects/simdutf/` with the
complete 8.2.0 source (the wrap's patch_directory adds the
meson.build/meson.options). Meson uses the vendored tree —
`wrap_mode=nodownload` does not break the build because no wrap
download is needed. The conan registry's `simdutf/6.0.3` is below the
required floor; no conan dependency is declared for simdutf.

## Upstream tests

- Tests are inline in `src/meson.build` (test_units): test-base16,
  test-colors, test-color-lightness, test-modes, test-parser,
  test-pastify, test-reaper, test-refptr, test-stream, test-tabstops,
  test-properties, test-unicode-width, test-utf8, test-uuid, plus
  gtk-flavour-conditional test-minifont-gtk4 (gtk3-only
  test-minifont-gtk3/test-vtetypes are NOT built with gtk3=false).
- Local run (`conan create` + direct exec): **15/15 test binaries
  rc=0** — including test-reaper ([parent] Quitting — pty available
  on this OHOS host via /data/service/hnp/bin/bash) and
  test-minifont-gtk4 (GDK_BACKEND=broadway headless). The recipe's
  `_run_parser_tests()` runs the no-display subset inside `build()`;
  the remainder was verified by direct exec with the same
  LD_LIBRARY_PATH assembly.
- Maintainer script tests (`doc syntax` check-doc-syntax.sh,
  `vte-urlencode-cwd` test-vte-urlencode-cwd.sh) need the upstream git
  tree / shell harness — not part of the release-tarball build.

## CI red #65549/#66114/#66132 root cause & fix

Three different CI workers failed identically at
`src/vteresources*.c/h` generation:

```
FAILED: [code=126] src/vteresources-gtk4.cc.c
.../glib.../p/bin/glib-compile-resources ...
/bin/sh: glib-compile-resources: Operation not permitted
```

Root cause: the registry glib/2.84.0.1.1 package ships its bin tools
(glib-compile-resources / glib-compile-schemas / gio-querymodules /
gobject-query / gtester / …) as OHOS aarch64 ELF executables whose
linker-time `.codesign` section is stale — OHOS XPM exec rejects them
(exit 126). Same recipe-side conditions as gtk4/4.22.4's R85/R86 fix
(proven on CI there).

Fix: `_re_sign_glib_tools()` in `generate()` re-signs every ELF file
in the resolved glib package's `bin/` in place
(llvm-objcopy --remove-section .codesign + binary-sign-tool
-selfSign), and puts glib's lib dir on LD_LIBRARY_PATH (the tools have
no RPATH — "Error loading shared library libgio-2.0.so.0" otherwise).
Verified locally: the previously rejected
glib-compile-resources execs fine after re-sign (--version → 2.84.0);
the build then passes the 126 wall and completes green.

## Consumer test

- `test_package/test.c` links `vte-2.91-gtk4`, verifies version
  macros (0.84.1), `vte_get_features()`, and the PCRE2-backed
  VteRegex substitute with an explicit expected-output comparison
  (`foobar` → `X`) — the E2E output-comparison form. Headless
  no-GDK path with full-widget fallback when a display exists.
