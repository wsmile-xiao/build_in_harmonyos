# nkt 0.3.1 HarmonyOS adaptation notes

## Scope and source

- Task: contrib-7176 (requester Hawkninja21, sourceUrl=null). The upstream is
  identified through the Homebrew formula `nkt` 0.3.1.
- Official release: `https://git.sr.ht/~fjebaker/nkt/archive/0.3.1.tar.gz`
- Verified SHA-256: `cfcede02c12cfe2fca4465fa3d87c03158202e4606c1ba3db46851dbb0451ccd`
  (matches the Homebrew formula).
- The Homebrew description ("TUI for interacting with your BibLaTeX database")
  is stale: the 0.3.1 sources are the terminal note-taking tool from the
  upstream README (journals, tasklists, notes, chains, tags, fuzzy find).
- Build system: Zig `build.zig` + `build.zig.zon`, Zig 0.15 era
  (`.fingerprint` manifest field, `std.Io.Writer` and `std.process.Child`
  0.15 APIs). License: GPL-3.0-or-later.

## Package identity

The package is `archives/n/nkt/0.3.1` with `name = "nkt"`, matching the
upstream project and binary name and the task branch `feat/nkt-0.3.1`
required by CI gate L0n (R40).

## Dependency analysis

Native (C) dependencies: none. nkt is a pure Zig application.

Build dependency:

- `zig/0.15.2`, published on the `ohpcd` Conan remote (recipe revision
  `501adb6c2fb136f4a58e15a2cb2d2412`, package ID
  `876049f3ae10a4560da345bb02378e03e212bc8c`). The recipe declares
  `tool_requires("zig/0.15.2")`, which resolves from the remote without a
  locally exported compiler.

Zig package dependencies (from `build.zig.zon`), all vendored offline:

| dependency | version | pinned commit | origin |
|---|---|---|---|
| termui | 0.2.2 | 9dc6d2fabb2a7305b07f2fc91f12770a321dded0 | github.com/fjebaker/termui |
| datetime | 0.8.0 | 3a39a21e6e34dcb0ade0ff828d0914d40ba535f3 | github.com/frmdstryr/zig-datetime |
| farbe | 0.3.1 | fa60dfeaaf049467a9158731bfbf930f0ca29f4e | github.com/fjebaker/farbe |
| clippy | 0.4.0 | 4eb7b412ce11e89314c3e83feeff9421292b4274 | github.com/fjebaker/clippy |
| fuzzig | 0.1.1 | 4251fe4230d38e721514394a485db62ee1667ff3 | github.com/fjebaker/fuzzig |
| kronos | 0.0.0 | a1d77455aeefe0656965548707ceeb6b85ff765e | git.sr.ht/~fjebaker/kronos |
| zeit (transitive, via kronos) | 0.6.0 | ade14edb2025f5e4a57b683f81c915f70a904e88 | github.com/rockorager/zeit |

All dep archives are declared in `conandata.yml` with their official URLs and
verified SHA-256 hashes. The CI's mirror-fallback/pre-download step covers the
github.com URLs automatically; git.sr.ht URLs are reachable directly.

## Offline vendoring design

CI devices cannot reach github.com directly (ConnectionResetByPeer), so
`zig build` fetching url dependencies would fail. The recipe (fancy-cat
0.6.0.1 pattern):

1. downloads the 7 dependency tarballs into `deps/<name>/` in `source()`;
2. rewrites the six url+hash entries of the root `build.zig.zon` to
   `.path = "deps/<name>"`;
3. rewrites kronos's own `build.zig.zon` zeit entry to `.path = "../zeit"`
   (`../` relative path deps work with zig 0.15.2 — proven by fancy-cat's
   vaxis → zigimg rewrite on device).

`zig build` and `zig build test` then run with zero network access. One
portability patch is applied after the dependency download (it targets a
vendored file, see the next section); the zon rewrite is a deterministic
string replacement in `source()`.

## Intended build and packaging

- Native build on the device: `zig build -j1 --prefix <stage>
  -Doptimize=ReleaseFast` (nkt's build.zig has no `-Dstrip` option).
- `zig build test -j1 --summary all` runs the full upstream test suite in the
  same recipe (R51); the parsed count is reported through
  `HMBS_UPSTREAM_TEST_RESULT`.
- Isolated zig caches under the Conan build folder
  (`ZIG_GLOBAL_CACHE_DIR`/`ZIG_LOCAL_CACHE_DIR`), `ZIG_OHOS_SIGN_ROOTS`
  covering caches and the install prefix for the tool package's
  generated-ELF signing.
- On OHOS, zig's libc probe keeps only the generic sysroot include directory;
  musl's `bits/` headers live in the target-specific directory, so the
  arch-specific include path is prepended to `CPATH` (ncdu 2.9.2 pattern).
- Install `bin/nkt` and the upstream `LICENSE`; sign the final ELF with
  `binary-sign-tool` on OHOS.

## Upstream tests

Static inventory: 21 test declarations across 9 source files
(`src/test/main.zig` contributes the `readme` and `smoke` integration tests
that drive the full command surface — help/init/config/new tag/log/task/ls/
read/edit — against a temporary root; the rest are unit tests in processing,
searching, selections, utils, Root, tags and Tasklist).

kronos `now()` uses a fixed timestamp under `builtin.is_test`, making the
suite deterministic; verified 21/21 under both `TZ=UTC` and
`TZ=Asia/Shanghai` on Linux x86_64 with zig 0.15.2.

## Patch: zeit TZDIR fallback (first CI run post-mortem)

The first GitCode CI run on this PR (worker CI-035, 2026-09-21) executed
the complete pipeline — all 8 downloads (sr.ht direct + gh-proxy mirror
fallback), offline vendoring, zon rewrite, ReleaseFast build, test
compilation — and then failed 3 of 21 upstream tests:

- `selections.test.resolve selections`
- `test.main.test.readme`
- `test.main.test.smoke`

All three failed identically: `error.FileNotFound` at
`deps/zeit/src/zeit.zig:121` (`dir.openFile`) called from
`deps/kronos/src/root.zig:141` (`initLocal`). Root cause chain:

1. kronos's test path (`builtin.is_test`) hardcodes
   `zeit.loadTimeZone(alloc, .@"Australia/Perth", null)` — a fixed
   timezone so `now()` is deterministic;
2. `zeit.loadTimeZone` consults TZDIR only through the explicit env-map
   argument; with `env = null` it skips straight to the well-known
   locations `/usr/share/zoneinfo`, `/share/zoneinfo`, `/etc/zoneinfo`;
3. the HarmonyOS device ships none of them with an `Australia/Perth`
   entry, so every test touching `kronos.TimeZone.initLocal` failed.

The local WSL run had passed because `/usr/share/zoneinfo/Australia/Perth`
exists there — the gap was invisible without the device.

Fix (patch `patches/zeit-tzdir-fallback.patch`, patch_type `portability`):
when `maybe_env` is null, fall back to the process environment's `TZDIR`
before the well-known locations. The change is 10 lines, additive, and
preserves the existing semantics for explicit env maps; it is upstreamable
as-is. The recipe decodes the Base64 tzfile into the build folder's
`zoneinfo/` (sha256-checked) and sets `TZDIR` there via
`Environment().define_path` for the test run, so the suite needs no system
tzdata at all.

Vendored data file `zoneinfo/Australia/Perth.b64`: the Base64 text
representation of the 446-byte TZif2 tzfile for Australia/Perth (decoded
sha256 `025d4339487853fa1f3144127959734b20f7c7b4948cff5d72149a0541a67968`),
extracted from Ubuntu tzdata `2024b-0ubuntu0.22.04.1` (IANA tzdata 2024b,
public domain). It is the exact file the WSL verification ran against. It
is time-zone data, not a precompiled binary (R19); Perth has had no DST
since 2009, so the file contains no future transition rules that could
interact with kronos's fixed test timestamp (2019-12-21).

Why Base64: the second CI run failed in the `checkout-pr` step before any
build started — the CI worker materializes a PR by downloading
`pull/11646.diff` and applying it with `git apply`, and GitCode's `.diff`
endpoint drops binary patch data (`Binary files /dev/null and ... differ`
with no `GIT binary patch` payload), so `git apply` aborts with "missing
binary patch data". A directly-committed binary file therefore cannot pass
CI checkout at all. The same constraint is documented in the merged clzip
1.16 recipe, which stores its compressed test fixture as
`res/test.txt.lz.b64` for exactly this reason. The recipe decodes the
Base64 into the build folder's `zoneinfo/` and enforces the sha256 above
on every build before the test run uses it.

Post-fix local verification (WSL): the patch applied cleanly to the
vendored zeit, and `zig build test -j1 --summary all` reports
`4/4 steps succeeded; 21/21 tests passed` with `TZDIR` pointing at a
directory containing only the vendored `Australia/Perth` — i.e. the exact
device conditions (no system zoneinfo). The `openDirAbsolute` call in the
patched branch requires an absolute `TZDIR`; the recipe always sets one
(`os.path.join(self.source_folder, "zoneinfo")`).

## Patch: zeit local() UTC fallback (third CI run post-mortem)

The third GitCode CI run (build #54409, worker CI-026, 2026-09-21) got
through everything the first two runs had fixed — 8 downloads, offline
vendoring, zon rewrite, ReleaseFast build, binary signing, and a green
`HMBS_UPSTREAM_TEST_RESULT` (21/21) — and then failed the consumer test:

```
AssertionError: command failed (1): ['.../p/bin/nkt', 'config']
stderr:
[error]: (default) FileNotFound
```

Root cause chain, established against the vendored sources and reproduced
exactly in WSL by moving `/etc/localtime` aside:

1. `nkt`'s `main()` calls `kronos.TimeZone.initLocal(allocator)` before
   dispatching any subcommand;
2. outside test builds that calls `zeit.local(alloc, null)` — a null env
   map, so zeit skips the `TZ` lookup entirely and opens
   `/etc/localtime` directly;
3. the HarmonyOS device ships no `/etc/localtime`, so the open fails with
   `FileNotFound`, the error escapes `main()`, and Zig 0.15's
   `std.start` reports it via `std.log.err("{s}", .{@errorName(err)})`;
4. nkt overrides the log function (`loggerFn`, src/main.zig) with the
   format `[level]: (scope) message` — hence the literal
   `[error]: (default) FileNotFound` on stderr and exit code 1.

This means the packaged binary failed on *every* invocation on the
device, not just under the consumer test — a product-level bug, invisible
in WSL because Ubuntu always has `/etc/localtime`. The first CI round
only exercised the test build (kronos hardcodes Australia/Perth there,
served by the TZDIR hunk above), and the author's WSL validation had a
system localtime, so the non-test path was never exercised without one.

Fix: a second hunk in the same `patches/zeit-tzdir-fallback.patch`
modifies the POSIX branch of `zeit.local` so a missing `/etc/localtime`
degrades to a fixed UTC zone instead of failing — mirroring kronos's own
documented fallback (`local()` accessor: "No local timezone: using UTC").
The change is two lines of comment plus replacing `try` with
`catch return utc`, is upstreamable, and preserves behaviour on systems
that do ship a localtime.

Local verification (WSL, 2026-09-21):

- reproduce: `mv /etc/localtime /etc/localtime.bak` → `nkt config`
  prints `[error]: (default) FileNotFound`, rc=1 (exact CI symptom);
- after applying the hunk and rebuilding ReleaseFast: without
  `/etc/localtime` → `nkt config` rc=0, `local time ...+00:00`; with it
  restored → `+08:00` as before;
- `zig build test -j1 --summary all` with the vendored-perth-only TZDIR
  → 21/21 still green (test path untouched);
- full `test_package/test_nkt.py` flow against the rebuilt binary with a
  fresh `$HOME` and no `/etc/localtime` (exact device conditions) →
  passes version/help/init/tag/log/read/ls.

## Upstream quirk: silent --version/--help

`nkt --version` and `nkt --help` exit 0 but print nothing: the early-return
path in `nkt_main` never flushes the buffered writer before
`std.process.exit`. The `config` and `help` subcommands are flushed by the
command executor and report the same information
(`nkt config` prints `nkt version : 0.3.1` and `nkt schema version : 0.5.0`).

CI gate L2 checks the exit code only, so it is unaffected. The consumer test
uses the subcommands.

## Consumer test

`test_package/test_nkt.py` is non-interactive and runs against the installed
binary:

1. asserts the exact version `0.3.1` and schema `0.5.0` via `nkt config`;
2. asserts ten core commands appear in `nkt help`;
3. initializes an isolated `NKT_ROOT_DIR` with `nkt init` and checks
   `config.json` is created;
4. creates a tag (`nkt new tag smoketag`);
5. logs an entry into the default diary journal (`nkt log`);
6. reads the journal back (`nkt read`) and asserts the logged text;
7. lists collections (`nkt ls`) and asserts the journal/tasklist sections.

The script was validated end-to-end against a locally built nkt 0.3.1 binary
on Linux x86_64.

## L0k commands.json

`nkt` is a command-line application, so repository gate L0k requires a
software-level `archives/n/nkt/commands.json`. This branch provides it with
`type = "tool"`, `name = "nkt"` and version `0.3.1`.

## Local verification (2026-09-21, Windows + WSL Ubuntu x86_64)

- All 8 archive SHA-256 hashes re-verified against the official sources.
- Dependency closure audited: no further transitive zig dependencies beyond
  kronos → zeit (all seven dep manifests inspected).
- Offline vendoring + zon rewrite executed exactly as the recipe does;
  dependency resolution needs zero network.
- Cross-compile: `zig build -Dtarget=aarch64-linux-musl -Doptimize=ReleaseFast`
  succeeds (zig 0.15.2, 7.7 MB binary).
- Native Linux: `zig build test --summary all` → 21/21 tests passed under
  `TZ=UTC` and `TZ=Asia/Shanghai`; `nkt config/help/init/new/log/read/ls`
  workflow validated; `test_nkt.py` passes unmodified.
- `conan graph info` with `ci/conan/profiles/ohos-aarch64` resolves
  `zig/0.15.2` (build) from `ohpcd` with no local dependency cache.
- Static checks: recipe and test files compile; YAML and JSON files parse;
  `git diff --check` is clean.
- Post-fix re-verification (after the first CI run, same day): patch +
  vendored Perth tzfile applied to the test tree; `zig build test
  --summary all` with `TZDIR` limited to the vendored zoneinfo directory
  → 21/21 tests passed (device conditions simulated).
- Post-fix re-verification (after the third CI run, same day): both
  patch hunks applied; without `/etc/localtime` the ReleaseFast binary
  runs the full command surface (UTC fallback) and `test_nkt.py` passes
  with a fresh `$HOME`; with `/etc/localtime` present the behaviour is
  unchanged; 21/21 upstream tests still green.

Not performed locally: `conan create` for HarmonyOS requires the aarch64/OHOS
zig binary and device; the first GitCode CI run on this PR provides the
HarmonyOS aarch64 build, upstream-test and consumer-test evidence, which will
be recorded in `manifest.yaml` once green.
