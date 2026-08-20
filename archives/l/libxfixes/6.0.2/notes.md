# libXfixes 6.0.2 adaptation notes

## Evidence status

- Source version: 6.0.2, the highest stable release listed by X.Org on
  2026-08-10.
- Source SHA256: `39f115d72d9c5f8111e4684164d3d68cc1fd21f9b27ff2401b08fddfc0f409ba`.
- Current main base: `f06dafbfc326bbbaf1bfcd423abe72b43dcf1654`.
- Fresh isolated OHOS/arm64 W0 passed for the complete dependency graph. Every
  remote node has RREV/PID/PREV, `binary_remote=ohpcd`, and empty
  `info_invalid`; exact evidence is in
  `E:/HarmonyPC/validation/libxfixes-6.0.2/w0-20260819-r14`.
- Exact-snapshot W3 r5 passed static and shared `conan create`, both installed
  package consumers, official `finish`, and `.ci-result.json` readback on
  `10.62.215.229:2222`. It binds candidate tree
  `0183a789e5851f9e3ddf13bf0dd29644bf350e3b` and bundle SHA256
  `eaf179f42cac67761fc4d66d2384b44cc361b0b3f4259902eb56e9f8a238d974`.
- W3 evidence is in
  `E:/HarmonyPC/validation/libxfixes-6.0.2/device-w3-20260819-r5`;
  at that W3 snapshot, independent W4 and the Pre-PR contract were still
  pending. The later gate status is recorded in the Resume condition below.

## Build design

The recipe uses the release Autotools files and preserves the upstream source
and library ABI. The native OHOS path uses `/system/bin/sh`, a package-local
temporary directory, and a build-local configure copy for the HMDFS umask
workaround. The release `configure` remains byte-identical; `generate()`
requires exactly two `umask 077` sites, writes only below `build_folder`, and
configure receives `--srcdir` for the untouched source tree. No source patch
is declared.

For frozen target validation, `LIBXFIXES_SOURCE_ARCHIVE` selects a verified
task-local release archive through a `file://` URI while retaining the official
SHA256 from `conandata.yml`. Normal builds continue to use the official URL.
Both `TMPDIR` and zsh `TMPPREFIX` are bound below the explicit task-local
temporary directory when the runner supplies one.

The first exact-snapshot target W3 reached the static configure stage and
failed before compilation because `config.guess` created a private temporary
subdirectory on HMDFS under an ownership-mapped Conan cache path. The target
compiler reports `aarch64-unknown-linux-ohos`, and the upstream `config.sub`
accepts that tuple. The successor therefore supplies the compiler-proven tuple
as both `--build` and `--host`, bypassing `config.guess`, and honors the
task-local `LIBXFIXES_TASK_TMPDIR`/`TMPDIR` instead of forcing cache-local
  temporary storage. The failed W3 root remains immutable evidence.

The next exact-snapshot static W3 then passed configure and compiled every
source file, but libtool loaded task-local `libX11.la` whose `dependency_libs`
and `libdir` still referenced obsolete default Conan cache paths. The recipe
now creates a build-local `libX11.la` shadow, uniquely rebinds missing Conan
`.la` paths to the current isolated dependency graph, rejects missing
non-Conan paths, and redirects generated `x11.pc` to the shadow. Dependency
package files remain unmodified.

The first fresh Windows graph-only W0 after this change reached `generate()`
and exposed a host/target path-boundary issue: Windows cannot prove that the
target-only `-L/storage/Users/currentUser/usr/local/lib` exists. Windows
graph-only generation now preserves explicit target POSIX `-L/` tokens while
still uniquely rebinding missing `.la` files and rejecting all other missing
non-Conan paths. The failed isolated r8 home is retained.

The isolated r9 install downloaded every required binary, then failed while
writing the shadow paths because `re.subn()` interpreted the backslashes in a
Windows replacement string as regular-expression escapes (`bad escape \H`).
Both path-bearing substitutions now use callable replacements, which preserve
the path bytes without replacement-string escape processing. The failed r9
home and its exact candidate archive remain retained.

The isolated r10 install then reached the final stale-archive check. On
Windows, `os.path.isabs('/storage/.../libxcb.la')` is false, so POSIX absolute
`.la` tokens had bypassed the basename rebinding branch. The cross-host check
now recognizes either a host-absolute path or a leading POSIX slash before
performing the same unique basename mapping. The failed r10 home is retained.

Fresh W0 r11 passed, but exact-snapshot device W3 r3 showed that AutotoolsDeps
placed the dependency package directories in global `LDFLAGS` before the
shadow path supplied by `x11.pc`. Libtool therefore selected the original
`libX11.la` and its obsolete transitive paths. The task-local build environment
now prepends `-L<build_folder>/libtool-shadow` before AutotoolsDeps appends the
real package directories; dependency packages remain unmodified. The consumed
r3 remote root and its byte-identical transfer evidence remain retained.

Exact-snapshot W3 r4 proved that the search-order correction selected the
sanitized direct archive, but libtool then recursively opened the current
`libxcb.la`, which itself referenced an obsolete `libXau.la`. The shadow now
covers every uniquely named `.la` in the resolved dependency graph, rewrites
all transitive `.la` references back into that shadow, copies each archive's
declared library files, and binds every shadow `libdir` locally. The consumed
r4 root remains immutable evidence; no dependency package cache was modified.

The isolated r13 generate exposed libxcb's target token
`//lib/libxcb.la`. Windows `Path` treats this as a UNC anchor and returns an
empty basename, while the target POSIX basename is `libxcb.la`. Leading-slash
tokens now use `PurePosixPath` for basename extraction; host-native paths keep
using `Path`. The failed r13 home remains retained.

Fresh W0 r14 then passed with 29 sanitized `.la` files, 87 copied library
files, zero stale cache tokens, and zero shadow-external `.la` references.
Exact-snapshot W3 r5 passed static and shared builds, upstream `make check`,
both package consumers in both option builds, official finish, and exact
result collection. The finish-generated `.ci-result.json` is 297 bytes with
SHA256 `275ad677ceb398d388ff5bf1233c402e613229e6854598f4c63ccb3dfbcaf5db`.

The first frozen W4 input had an empty `diff_stat`, so its findings are useful
observations but not formal closure. Before refreezing, the assertion metadata
was corrected from 55 to the mechanically verified 56 checks, and the R6-risk
in-place configure rewrite was replaced with the build-local design. Focused
validators bind both corrections to the current recipe and official source.

## Dependency boundary

- `libx11/1.8.13`: direct linked dependency.
- `xorgproto/2025.1`: direct public protocol-header dependency.

libXext and libXrender are not direct requirements. The xtrans/libxcb/libXau/
libXdmcp closure remains owned by the libX11 recipe.

## Test inventory

The release registers no Automake `TESTS`, `check_PROGRAMS`, `check-local`, or
Meson `test()` entry. The truthful upstream count is therefore 0/0.

Two installed-package consumers passed in both static and shared builds:

1. `libxfixes_api_surface` forces relocations for all 37 public functions and
   calls the display-independent `XFixesVersion()` API.
2. `libxfixes_version_contract` validates protocol/version constants and
   public ABI types, then calls `XFixesVersion()`.

The exact W3 result is `2/2` shared and `2/2` static. Upstream `make check`
completed in both builds with the truthful upstream inventory `0/0`.

## Resume condition

W5 knowledge deduplication and the final independent W4 are complete. Pass the
Pre-PR contract next. PR #5559 and the competing 6.1.0 task remain open, so
push and PR creation stay prohibited.
---

**编译结束**: 2026-08-19 22:56
**最终状态**: built (exact-snapshot static/shared W3 and official finish passed)
